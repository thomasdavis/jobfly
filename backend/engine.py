import hashlib
import json
import math
import os
import threading
import time

os.environ.setdefault("NUMBA_NUM_THREADS", "2")
os.environ.setdefault("FLY_DATA", "/mnt/donto-data/donto-resources/research/jobfly-runtime/brain")
import numpy as np
from .circuit import CircuitBrain
from .learning import RewardPlasticity
from .swarm import SwarmPolicy as NeuralPolicy
from .senses import MODEL, semantic_vectors, cache_public_vectors
from .storage import Store


class Engine:
    def __init__(self, state_directory=None):
        self.lock = threading.RLock()
        self.status, self.error = "loading", None
        self.loading_stage = "Loading the connectome"
        self.running = True
        self.clients = 0
        self.revision = 0
        self.brain = self.policy = None
        self.store = Store(state_directory) if state_directory else Store()
        self.jobs, self.marks, self.reasons = [], {}, {}
        self.resume = None
        self.source = "jsonresume"
        self.learning_enabled = True
        self.spikes = []
        self.step_ms = 0
        self.total_spikes = 0
        self.stopped = False
        self.rng = np.random.default_rng(64)
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def _worker(self):
        try:
            self.brain = CircuitBrain(device="cpu")
            self.plastic = RewardPlasticity(self.brain)
            self.steer = [self.brain.groups[f"steer_{s}"] for s in "LR"]
            saved = self.store.latest()
            neural = {}
            if saved:
                self.jobs, self.marks = saved["jobs"], saved["marks"]
                self.reasons = saved.get("reasons", {})
                self.resume = saved.get("resume")
                self.source = saved.get("source", "jsonresume")
                if "factors" in saved:
                    self.plastic.restore(saved["factors"], saved["updates"])
                neural = saved.get("neural", {})
                if self.resume and self.source != "example" and len(self.jobs) < 500 and neural.get("version", 0) < 3:
                    self.loading_stage = "Opening the larger job catalog"
                    from .jobs import fetch_resume_jobs
                    try:
                        expanded = fetch_resume_jobs(self.resume)
                        self.jobs = list({j["url"]: j for j in [*expanded, *self.jobs] if j.get("url")}.values())
                    except Exception:
                        pass  # Keep the saved real catalog if its source is temporarily down.
                if self.source == "example":
                    self.jobs, self.resume = [], None
            self._encode(neural)
            self._map()
            self.status = "ready"
            self.persist()
            while not self.stopped:
                start = time.perf_counter()
                with self.lock:
                    if self.running and self.clients and self.jobs:
                        self._advance()
                time.sleep(max(.005, .10 - (time.perf_counter() - start)))
            with self.lock:
                self.persist()
        except Exception as exc:
            import traceback
            traceback.print_exc()
            self.status, self.error = "error", str(exc)

    def _encode(self, neural=None):
        neural = neural or {}
        from .job_feed import plain_description
        self.jobs = [dict(j, description=plain_description(j.get("description"))) for j in self.jobs]
        self.world_radius = max(8., math.sqrt(len(self.jobs)) * 1.15)
        for i, job in enumerate(self.jobs):
            angle = i * 2.399963
            radius = self.world_radius * .92 * math.sqrt((i + .5) / len(self.jobs))
            job["x"], job["z"] = float(math.cos(angle) * radius), float(math.sin(angle) * radius)
        self.revision += 1
        self.loading_stage = "Reading the resume and jobs"
        self.input_digest = hashlib.sha256(json.dumps([[{k: v for k, v in j.items() if k not in ("x", "z")} for j in self.jobs], self.resume, MODEL, 3], sort_keys=True).encode()).hexdigest()
        cached = np.asarray(neural.get("vectors", []), np.float32)
        if neural.get("inputDigest") == self.input_digest and cached.shape == (len(self.jobs) + 1, 384) and np.isfinite(cached).all():
            self.vectors = cached
            cache_public_vectors(self.jobs, cached)
        else:
            self.vectors = semantic_vectors(self.jobs, self.resume, progress=lambda text: setattr(self, "loading_stage", text))
        # Coordinates are rendering/body geometry, never candidate score inputs.
        self.loading_stage = "Calibrating neural movement"
        self.policy = NeuralPolicy(self.brain, self.plastic, self.jobs, self.vectors,
                                   samples=neural.get("samples"), radius=self.world_radius, saved=neural.get("ecosystem"))
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
        classes[self.brain.superclass == "descending_neuron"] = 3
        classes[self.policy.senses.orn] = 4
        for ids in self.plastic.modulators.values():
            classes[ids] = 5
        self.map_data = dict(positions=xyz.round(4).flatten().tolist(),
                             classes=classes[valid].tolist(), neurons=self.brain.n,
                             connections=len(self.brain.weights), mapped=len(valid),
                             learningEdges=len(self.plastic.edges), kc=len(self.plastic.kc),
                             mbon=len(self.plastic.mbon))

    def _advance(self):
        frame = []
        started = time.perf_counter()
        for _ in range(5):
            frame.extend(self.policy.tick(self.learning_enabled, self.marks).tolist())
        self.step_ms = (time.perf_counter() - started) * 200
        if self.policy.checkpoint_due:
            self.persist()
            self.policy.checkpoint_due = False
        self.total_spikes = len(frame)
        mapped = self.pos_index[np.unique(frame).astype(np.int64)]
        mapped = mapped[mapped >= 0]
        if len(mapped) > 3500:
            mapped = self.rng.choice(mapped, 3500, replace=False)
        self.spikes = mapped.tolist()

    @property
    def landed(self):
        return self.policy.landed if self.policy else None

    def snapshot(self):
        with self.lock:
            ready = self.status == "ready"
            p = self.policy if ready else None
            return dict(status=self.status, error=self.error, loadingStage=self.loading_stage,
                        running=self.running, fly=p.fly.copy() if p else dict(x=0., z=0., heading=0.),
                        target=self.jobs[p.target]["id"] if p and p.target is not None else None,
                        attending=self.jobs[p.attending]["id"] if p and p.attending is not None else None,
                        landed=self.landed, spikes=self.spikes, totalSpikes=self.total_spikes,
                        motor=[p.turn, p.speed, p.brake] if p else [0, 0, 0],
                        drive=[max(0, -getattr(p, "direction", 0)), max(0, getattr(p, "direction", 0))],
                        stepMs=round(self.step_ms, 2), elapsed=round(p.elapsed, 2) if p else 0,
                        revision=self.revision, source=self.source, updates=self.plastic.updates if ready else 0,
                        changed=self.plastic.changed if ready else 0, landings=p.landings if p else 0,
                        learning=self.learning_enabled and bool(p and p.brain.intervention == "intact"), marks=self.marks,
                        preferences={key: round(p.decoder.predict(value), 5) for key, value in p.features.items()} if p else {},
                        phase=p.phase if p else "loading", scan=dict(done=p.cursor, total=len(p.queue)) if p else None,
                        evidence=p.evidence if p else {}, intervention=self.brain.intervention if p else "intact",
                        activeNeurons=int(self.brain.ever_active.sum()) if p else 0,
                        inputNeurons=len(p.senses.driven) if p else 0,
                        decoderSamples=len(p.decoder.samples) if p else 0,
                        calibration=p.motor_decoder.calibration if p else None,
                        reward=p.last_reward if p else None, decision=p.decision if p else None,
                        policyVersion=NeuralPolicy.version, encoder=MODEL,
                        swarm=p.public_flies() if p else [], ecosystem=p.summary() if p else None, worldRadius=getattr(self, "world_radius", 8))

    def persist(self, feedback=None):
        p = self.policy
        self.store.save(dict(jobs=self.jobs, marks=self.marks, reasons=self.reasons, resume=self.resume,
                             source=self.source, factors=self.plastic.factors.tolist(), updates=self.plastic.updates,
                             neural=dict(version=NeuralPolicy.version, inputDigest=self.input_digest,
                                         vectors=self.vectors.tolist(), samples=p.decoder.samples, ecosystem=p.checkpoint())), feedback)

    def feedback(self, job_id, reward, reason):
        with self.lock:
            if not self.learning_enabled:
                raise ValueError("Enable learning before giving feedback.")
            changed = self.policy.reward(job_id, reward)
            self.marks[job_id] = "liked" if reward > 0 else "passed"
            self.reasons[job_id] = reason
            self.persist((job_id, reward, reason, changed))
            return changed

    def depart(self):
        self.policy.depart()

    def focus(self, job_id):
        index = next((i for i, j in enumerate(self.jobs) if j["id"] == job_id), None)
        if index is None:
            raise ValueError("Job not found.")
        self.policy.focus(index)
        self.running = True

    def replace_jobs(self, jobs, source, resume=None):
        with self.lock:
            self.running = False
            samples = self.policy.decoder.samples if self.policy else {}
            self.jobs, self.source, self.resume = jobs, source, resume
            self._encode(dict(samples=samples))
            self.persist()
