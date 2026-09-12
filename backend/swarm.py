"""Time-multiplexed full-connectome swarm, with shared learned weights.

Each fly owns its attention, body, and candidate history. A single full network
executes matched recurrent windows for them in turn. This is not 24 independent
simultaneously integrated biological brains, nor 24 decorative copies of a fly.
"""
import math
import numpy as np

from .policy import NeuralPolicy
from .motor import STEPS


class SwarmPolicy:
    version = 3
    count = 24
    settle_seconds = 120

    def __init__(self, brain, plastic, jobs, vectors, samples=None, radius=8, saved=None):
        self.brain, self.plastic, self.jobs = brain, plastic, jobs
        self.radius = radius
        self.rng = np.random.default_rng(390)
        self.elapsed = float((saved or {}).get("elapsed", 0))
        self.observations = (saved or {}).get("observations", {})
        self.observations = {k: v for k, v in self.observations.items() if any(j["id"] == k for j in jobs)}
        self.checkpoint_due = False
        self.last_checkpoint = self.elapsed
        self.active = 0
        first = NeuralPolicy(brain, plastic, jobs, vectors, samples)
        self.flies = [first] + [NeuralPolicy(brain, plastic, jobs, vectors, shared=first) for _ in range(self.count - 1)]
        self.senses, self.decoder, self.motor_decoder = first.senses, first.decoder, first.motor_decoder
        self.features = {}
        self.last_reward = None
        self.resume_ready = False
        self.resume_baseline = None
        self.resume_counts = np.zeros(brain.n, np.float32)
        self.resume_step = 0
        self.resume_phase = "baseline"
        self.landings = int((saved or {}).get("landings", 0))
        for i, fly in enumerate(self.flies):
            angle = i * 2.399963
            r = radius * .8 * math.sqrt((i + .5) / self.count)
            fly.fly = dict(x=math.cos(angle) * r, z=math.sin(angle) * r, heading=angle)
            fly.radius = radius
            fly.sensory_gain = .85 + .3 * i / max(1, self.count - 1)
            fly.dwell_until = 0
            fly.moving_windows = 0
            self._round(fly)
        self.brain.reset(64)

    def __getattr__(self, name):
        # Legacy HUD fields refer to the fly currently receiving neural compute.
        return getattr(self.flies[self.active], name)

    def _round(self, fly):
        fly.new_round()
        fly.records.clear()  # Keep full-neuron traces bounded to three candidates.
        fly.features.clear()
        if not self.jobs:
            return
        available = np.arange(len(self.jobs))
        visits = np.array([self.observations.get(j["id"], {}).get("visits", 0) for j in self.jobs])
        # Coverage is an exploration schedule, not a job suitability score.
        novel = available[visits == visits.min()]
        explore = int(self.rng.choice(novel))
        distance = np.array([(j["x"] - fly.fly["x"]) ** 2 + (j["z"] - fly.fly["z"]) ** 2 for j in self.jobs])
        local = int(self.rng.choice(np.argsort(distance)[:min(24, len(self.jobs))]))
        measured = [i for i, j in enumerate(self.jobs) if j["id"] in self.features]
        if measured:
            best = sorted(measured, key=lambda i: self.decoder.predict(self.features[self.jobs[i]["id"]]), reverse=True)[:12]
            recruited = int(self.rng.choice(best))
        else:
            recruited = int(self.rng.choice(available))
        fly.queue = list(dict.fromkeys([explore, local, recruited]))
        fly.moving_windows = 0

    def _reference(self):
        # The resume is presented through the same ORNs, not used as a text score.
        if self.resume_phase == "resume":
            self.senses.inject_odor(len(self.jobs))
        fired = self.brain.step()
        self.resume_counts[fired] += 1
        self.resume_step += 1
        if self.resume_step == STEPS:
            if self.resume_phase == "baseline":
                self.resume_baseline = self.resume_counts.copy()
                self.resume_phase = "resume"
            else:
                features, _ = self.flies[0].project.encode(self.resume_counts - self.resume_baseline)
                self.decoder.initial = features.copy()
                self.resume_ready = True
            self.resume_step = 0
            self.resume_counts[:] = 0
            self.brain.reset(64)
        return fired

    def tick(self, learning=True, legacy_marks=None):
        if not self.jobs:
            return np.empty(0, np.int64)
        self.elapsed += self.brain.dt
        if not self.resume_ready:
            return self._reference()
        fly = self.flies[self.active]
        old_phase, index = fly.phase, fly.attending
        fired = fly.tick(learning, legacy_marks)
        if fly.window_step == 0:
            if old_phase == "comparing" and index is not None:
                key = self.jobs[index]["id"]
                self.features[key] = fly.features[key].copy()
                evidence = fly.evidence[key]
                if evidence["response"] > 1e-6:
                    item = self.observations.setdefault(key, dict(visits=0, flies=[], first=self.elapsed, last=self.elapsed, landings=0))
                    item["visits"] += 1
                    item["last"] = self.elapsed
                    item["response"] = evidence["response"]
                    item["value"] = self.decoder.predict(self.features[key])
                    if self.active not in item["flies"]:
                        item["flies"].append(self.active)
            if old_phase == "moving":
                fly.moving_windows += 1
                if fly.landed:
                    self.landings += 1
                    if fly.landed in self.observations:
                        self.observations[fly.landed]["landings"] += 1
                    fly.dwell_until = self.elapsed + 12 + 24 * max(0, self.decoder.predict(self.features.get(fly.landed, np.zeros(512))))
                elif fly.moving_windows >= 14:
                    # Attention can expire; a timed-out approach is NOT a landing.
                    self._round(fly)
            self.active = (self.active + 1) % self.count
            for _ in range(self.count):
                next_fly = self.flies[self.active]
                if next_fly.phase == "landed" and self.elapsed >= next_fly.dwell_until:
                    self._round(next_fly)
                if next_fly.phase not in ("landed", "no_response"):
                    break
                self.active = (self.active + 1) % self.count
            self.brain.reset(64)
        if self.elapsed - self.last_checkpoint >= 60:
            self.checkpoint_due = True
            self.last_checkpoint = self.elapsed
        return fired

    def public_flies(self):
        return [dict(id=i, **f.fly, phase=f.phase, target=self.jobs[f.target]["id"] if f.target is not None else None,
                     attending=self.jobs[f.attending]["id"] if f.attending is not None else None,
                     landed=f.landed, motor=[f.turn, f.speed, f.brake], active=i == self.active)
                for i, f in enumerate(self.flies)]

    def summary(self):
        entries = {}
        for key, item in self.observations.items():
            value = self.decoder.predict(self.features[key]) if key in self.features else item.get("value", 0)
            mature = (self.elapsed >= self.settle_seconds and self.elapsed - item["first"] >= 30 and len(item["flies"]) >= 3)
            entries[key] = dict(visits=item["visits"], flies=len(item["flies"]), landings=item["landings"],
                                value=round(value, 5), mature=mature)
        ranked = sorted((k for k in entries if entries[k]["mature"] and entries[k]["value"] > 0),
                        key=lambda k: entries[k]["value"], reverse=True)[:12]
        return dict(explored=len(entries), total=len(self.jobs), settling=self.elapsed < self.settle_seconds,
                    minimumSeconds=self.settle_seconds, recommendations=ranked, activity=entries,
                    activeFly=self.active, sharedBrain=True)

    def checkpoint(self):
        return dict(elapsed=self.elapsed, observations=self.observations, landings=self.landings)

    def reward(self, identifier, value):
        if self.brain.intervention != "intact":
            raise ValueError("Restore the intact circuit before teaching the swarm.")
        index = next((i for i, j in enumerate(self.jobs) if j["id"] == identifier), None)
        if index is None:
            raise ValueError("Job not found.")
        fly = self.flies[self.active]
        # Optional feedback works on any real job, independent of landing state.
        measurements = []
        for odor in (False, True):
            self.brain.reset(64)
            counts = np.zeros(self.brain.n, np.float32)
            for _ in range(STEPS):
                if odor:
                    self.senses.inject_odor(index)
                counts[self.brain.step()] += 1
            measurements.append(counts)
        response = measurements[1] - measurements[0]
        features, _ = fly.project.encode(response)
        fly.records[identifier] = (np.maximum(response[self.plastic.kc], 0), measurements[1])
        fly.features[identifier] = features
        changed = fly.reward(identifier, value)
        self.features[identifier] = features.copy()
        self.last_reward = fly.last_reward
        # Discard an interrupted neural window, not any visitor feedback.
        fly._window()
        return changed

    def focus(self, index):
        fly = self.flies[self.active]
        self._round(fly)
        fly.queue = list(dict.fromkeys([index, *fly.queue]))[:3]
        fly.attention = index

    def depart(self):
        self._round(self.flies[self.active])

    def intervene(self, name):
        self.brain.intervene(name)
        self.features.clear()
        self.observations.clear()
        for fly in self.flies:
            fly.turn = fly.speed = fly.brake = 0
            self._round(fly)
        self.resume_ready = False
        self.resume_phase = "baseline"
        self.resume_step = 0
        self.resume_counts[:] = 0
        self.brain.reset(64)
