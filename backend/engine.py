import math
import os
import threading
import time
from pathlib import Path

os.environ.setdefault("NUMBA_NUM_THREADS", "4")
os.environ.setdefault("FLY_DATA", "/mnt/donto-data/donto-resources/research/jobfly-runtime/brain")
import numpy as np
from .vendor.fly_ai.fly_brain import FlyBrain
from .jobs import SensoryEncoder, examples
from .learning import RewardPlasticity
from .storage import Store


class Engine:
    def __init__(self, state_directory=None):
        self.lock = threading.RLock()
        self.status, self.error = "loading", None
        self.running = False
        self.clients = 0
        self.revision = 0
        self.brain = None
        self.store = Store(state_directory) if state_directory else Store()
        self.jobs, self.marks, self.reasons = examples(), {}, {}
        self.resume = None
        self.source = "example"
        self.learning_enabled = True
        self.fly = dict(x=0., z=0., heading=0.)
        self.target = None
        self.landed = None
        self.cooldowns = {}
        self.motor = np.zeros(2)
        self.drive = [0., 0.]
        self.spikes = []
        self.step_ms = 0
        self.total_spikes = 0
        self.landings = 0
        self.elapsed = 0.
        self.stopped = False
        self.rng = np.random.default_rng(64)
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def _worker(self):
        try:
            self.brain = FlyBrain(device="cpu", seed=64)
            self.plastic = RewardPlasticity(self.brain)
            self.steer = [self.brain.groups[f"steer_{s}"] for s in "LR"]
            self.chase = [self.brain.cells(["LC10a"], side=s) for s in "LR"]
            saved = self.store.latest()
            if saved:
                self.jobs, self.marks = saved["jobs"], saved["marks"]
                self.reasons = saved.get("reasons", {})
                self.resume = saved.get("resume")
                self.source = saved.get("source", "example")
                self.plastic.restore(saved["factors"], saved["updates"])
            self._encode()
            self._map()
            # Warm the Numba kernel before announcing ready.
            self.brain.step()
            self.status = "ready"
            while not self.stopped:
                start = time.perf_counter()
                with self.lock:
                    if self.running and self.clients and self.landed is None:
                        self._advance()
                time.sleep(max(.005, .10 - (time.perf_counter() - start)))
        except Exception as exc:
            import traceback
            traceback.print_exc()
            self.status, self.error = "error", str(exc)

    def _encode(self):
        self.encoder = SensoryEncoder(self.jobs, len(self.plastic.kc))
        for i, job in enumerate(self.jobs):
            # Stable angular layout adds separation to the learned projection.
            angle = i * 2.399963
            radius = 2.6 + 3.4 * math.sqrt((i + .5) / len(self.jobs))
            job["x"] = float(math.cos(angle) * radius + self.encoder.coordinates[i, 0] * .6)
            job["z"] = float(math.sin(angle) * radius + self.encoder.coordinates[i, 1] * .6)
        self.revision += 1

    def _map(self):
        positions = self.brain.positions
        valid = np.flatnonzero(np.isfinite(positions).all(axis=1))
        self.mapped = valid
        self.pos_index = np.full(self.brain.n, -1, dtype=np.int32)
        self.pos_index[valid] = np.arange(len(valid))
        xyz = positions[valid].copy()
        xyz -= (np.nanpercentile(xyz, 99, axis=0) + np.nanpercentile(xyz, 1, axis=0)) / 2
        xyz /= np.max(np.abs(xyz))
        # EM z is the long brain-to-cord axis; render vertically.
        xyz = xyz[:, [0, 2, 1]]
        xyz[:, 1] *= -1
        classes = np.zeros(self.brain.n, np.uint8)
        classes[self.plastic.kc] = 1
        classes[self.plastic.mbon] = 2
        for group in self.steer:
            classes[group] = 3
        self.map_data = dict(positions=xyz.round(4).flatten().tolist(),
                             classes=classes[valid].tolist(), neurons=self.brain.n,
                             connections=len(self.brain.weights), mapped=len(valid),
                             learningEdges=len(self.plastic.edges), kc=len(self.plastic.kc),
                             mbon=len(self.plastic.mbon))

    def _pick_target(self):
        options = [i for i, j in enumerate(self.jobs) if self.cooldowns.get(j["id"], 0) <= self.elapsed]
        if not options:
            options = list(range(len(self.jobs)))
        scores = []
        for i in options:
            j = self.jobs[i]
            distance = math.hypot(j["x"] - self.fly["x"], j["z"] - self.fly["z"])
            learned = self.plastic.preference(self.encoder.codes[i]) if self.learning_enabled else 0
            scores.append(learned * 12 - distance * .10 - (.8 if j["id"] in self.marks else 0))
        p = np.exp(np.asarray(scores) - max(scores))
        self.target = int(self.rng.choice(options, p=p / p.sum()))
        self.plastic.eligibility[:] = 0

    def _advance(self):
        if self.target is None:
            self._pick_target()
        job = self.jobs[self.target]
        dx, dz = job["x"] - self.fly["x"], job["z"] - self.fly["z"]
        angle = math.atan2(dx, dz)
        error = math.atan2(math.sin(angle - self.fly["heading"]), math.cos(angle - self.fly["heading"]))
        side = 1 if error > 0 else 0
        self.drive = [0., 0.]
        self.drive[side] = .65
        code = self.encoder.codes[self.target]
        scent = self.plastic.kc[code > 0]
        frame = []
        started = time.perf_counter()
        for _ in range(5):
            fired = self.brain.step(inject=[(self.chase[side], .65), (scent, .22)])
            self.plastic.observe(fired)
            self.motor *= .92
            self.motor += np.array([np.isin(fired, group).sum() for group in self.steer])
            frame.extend(fired.tolist())
        self.step_ms = (time.perf_counter() - started) * 200
        self.elapsed += .1
        self.total_spikes = len(frame)
        unique = np.unique(frame)
        mapped = self.pos_index[unique]
        mapped = mapped[mapped >= 0]
        if len(mapped) > 3500:
            mapped = self.rng.choice(mapped, 3500, replace=False)
        self.spikes = mapped.tolist()
        # Descending-neuron steering drives a simple kinematic body.
        turn = float(np.tanh((self.motor[1] - self.motor[0]) * .8))
        self.fly["heading"] += turn * .19
        speed = .13 * (1 - .7 * min(abs(error) / math.pi, 1))
        self.fly["x"] += math.sin(self.fly["heading"]) * speed
        self.fly["z"] += math.cos(self.fly["heading"]) * speed
        # World is a torus; boundaries wrap, no invisible steering override.
        for axis in ("x", "z"):
            self.fly[axis] = (self.fly[axis] + 8) % 16 - 8
        if math.hypot(dx, dz) < .95:
            self.landed = job["id"]
            self.landings += 1
            # Credit recent firing in the presented scent ensemble, not unrelated
            # background spikes throughout the brain.
            self.landing_trace = self.plastic.eligibility.copy() * code

    def snapshot(self):
        with self.lock:
            ready = self.status == "ready"
            return dict(status=self.status, error=self.error, running=self.running,
                        fly=self.fly.copy(), target=self.jobs[self.target]["id"] if self.target is not None else None,
                        landed=self.landed, spikes=self.spikes, totalSpikes=self.total_spikes,
                        motor=self.motor.round(3).tolist(), drive=self.drive, stepMs=round(self.step_ms, 2),
                        elapsed=round(self.elapsed, 1), revision=self.revision, source=self.source,
                        updates=self.plastic.updates if ready else 0,
                        changed=self.plastic.changed if ready else 0, landings=self.landings,
                        learning=self.learning_enabled, marks=self.marks,
                        preferences={j["id"]: round(self.plastic.preference(self.encoder.codes[i]), 4) for i, j in enumerate(self.jobs)} if ready else {})

    def persist(self, feedback=None):
        self.store.save(dict(jobs=self.jobs, marks=self.marks, reasons=self.reasons, resume=self.resume,
                             source=self.source, factors=self.plastic.factors.tolist(), updates=self.plastic.updates), feedback)

    def feedback(self, job_id, reward, reason):
        with self.lock:
            if self.landed != job_id:
                raise ValueError("Wait for the fly to land on this job before teaching it.")
            if not self.learning_enabled:
                raise ValueError("Enable learning before giving feedback.")
            changed = self.plastic.reward(reward, self.landing_trace)
            self.marks[job_id] = "liked" if reward > 0 else "passed"
            self.reasons[job_id] = reason
            self.persist((job_id, reward, reason, changed))
            self.depart()
            return changed

    def depart(self):
        if self.landed:
            self.cooldowns[self.landed] = self.elapsed + 60
        self.landed, self.target = None, None

    def replace_jobs(self, jobs, source, resume=None):
        with self.lock:
            self.running = False
            self.jobs, self.source, self.resume = jobs, source, resume
            self.fly = dict(x=0., z=0., heading=0.)
            self.landed, self.target = None, None
            self.cooldowns = {}
            self._encode()
            self.persist()
