"""Attention sweeps, measured neural evidence, and decoded movement.

Every candidate is presented to the full recurrent network. Only the measured
response enters the learned decoder. There is no text/rank/distance job scorer.
"""
import math

import numpy as np

from .circuit import ActivityProjection, ActivityReadout
from .motor import MotorDecoder, STEPS
from .senses import Sensorium


class NeuralPolicy:
    version = 2

    def __init__(self, brain, plastic, jobs, vectors, samples=None, shared=None, motor=None, continuous=False):
        self.continuous = continuous
        self.brain, self.plastic, self.jobs = brain, plastic, jobs
        self.senses = shared.senses if shared else Sensorium(brain, vectors)
        self.project = shared.project if shared else ActivityProjection(brain, self.senses.driven)
        self.decoder = shared.decoder if shared else ActivityReadout()
        if samples:
            self.decoder.restore(samples)
        self.motor_decoder = motor if motor is not None else (shared.motor_decoder if shared else MotorDecoder(brain, self.senses))
        self.baseline = self.motor_decoder.baseline.copy()
        self.evidence, self.features, self.records = {}, {}, {}
        self.cooldowns = {}
        self.attention = None
        self.target = self.landed = None
        self.fly = dict(x=0., z=0., heading=0.)
        self.turn = self.speed = self.brake = 0.
        self.elapsed = 0.
        self.landings = 0
        self.last_reward = None
        self.decision = None
        self.history = []
        self.brain.ever_active[:] = False
        self.new_round()

    def _window(self):
        # Matched initial states and noise make each candidate measurement
        # reproducible. Recurrence unfolds within the full 640 ms window.
        if not self.continuous:
            self.brain.reset(64)
        self.counts = np.zeros(self.brain.n, np.float32)
        self.window_step = 0

    def new_round(self):
        self.target = self.landed = None
        self.phase = "baseline"
        self.queue = [i for i, j in enumerate(self.jobs) if self.cooldowns.get(j["id"], 0) <= self.elapsed]
        if not self.queue:
            self.queue = list(range(len(self.jobs)))
        self.cursor = 0
        self.evidence = {}
        self._window()

    @property
    def attending(self):
        return self.queue[self.cursor] if self.phase == "comparing" and self.cursor < len(self.queue) else None

    def tick(self, learning=True, legacy_marks=None):
        if self.phase in ("landed", "no_response") or not self.jobs:
            return np.empty(0, np.int64)
        eye = None
        if self.phase == "comparing":
            index = self.attending
            self.senses.inject_odor(index, getattr(self, "sensory_gain", 1.) * (1.15 if index == self.attention else 1.))
        elif self.phase == "moving":
            job = self.jobs[self.target]
            dx, dz = job["x"] - self.fly["x"], job["z"] - self.fly["z"]
            error = math.atan2(dx, dz) - self.fly["heading"]
            error = math.atan2(math.sin(error), math.cos(error))
            self.direction = float(np.clip(error / (math.pi / 2), -1, 1))
            distance = math.hypot(dx, dz)
            self.intensity = .65 + .75 * math.exp(-distance / 1.8)
            eye = self.senses.vision(self.direction, self.intensity)
        fired = self.brain.step(eye_drive=eye)
        self.counts[fired] += 1
        self.window_step += 1
        self.elapsed += self.brain.dt
        if self.window_step < STEPS:
            return fired
        if self.phase == "baseline":
            self.baseline = self.counts.copy()
            self.phase = "comparing"
        elif self.phase == "comparing":
            index = self.attending
            identifier = self.jobs[index]["id"]
            response = self.counts - self.baseline
            features, energy = self.project.encode(response)
            self.features[identifier] = features
            self.records[identifier] = (np.maximum(response[self.plastic.kc], 0), self.counts.copy())
            # Adopt old explicit feedback once using newly measured responses;
            # no old marks are turned directly into candidate scores.
            if learning and legacy_marks and identifier in legacy_marks and identifier not in self.decoder.samples and self.brain.intervention == "intact":
                self.decoder.learn(identifier, features, 1 if legacy_marks[identifier] == "liked" else -1)
            score = self.decoder.predict(features)
            self.evidence[identifier] = dict(value=round(score, 5), response=round(energy, 3))
            self.cursor += 1
            if self.cursor == len(self.queue):
                responsive = [i for i in self.queue if self.evidence[self.jobs[i]["id"]]["response"] > 1e-6]
                if not responsive:
                    self.phase = "no_response"
                else:
                    self.target = max(responsive, key=lambda i: self.evidence[self.jobs[i]["id"]]["value"])
                    self.phase = "motor_baseline" if self.continuous else "moving"
                    self.decision = dict(jobId=self.jobs[self.target]["id"], elapsed=round(self.elapsed, 2),
                                         intervention=self.brain.intervention, evidence=dict(self.evidence))
                    self.history.append(self.decision)
                    self.history = self.history[-20:]
            elif self.continuous:
                self.phase = "baseline"
        elif self.phase == "motor_baseline":
            self.baseline = self.counts.copy()
            self.phase = "moving"
        elif self.phase == "moving":
            self.turn, self.speed, self.brake = self.motor_decoder.decode(self.counts, self.baseline)
            dt = STEPS * self.brain.dt * (2 if self.continuous else 1)
            self.fly["heading"] += self.turn * 2.2 * dt
            distance = self.speed * 2.3 * dt
            self.fly["x"] += math.sin(self.fly["heading"]) * distance
            self.fly["z"] += math.cos(self.fly["heading"]) * distance
            for axis in ("x", "z"):
                self.fly[axis] = float(np.clip(self.fly[axis], -getattr(self, "radius", 8), getattr(self, "radius", 8)))
            job = self.jobs[self.target]
            # Collision is body geometry; contact alone is insufficient. The
            # neural braking channel must also engage before a landing registers.
            if math.hypot(job["x"] - self.fly["x"], job["z"] - self.fly["z"]) < .95 and self.brake > .15:
                self.landed = job["id"]
                self.landings += 1
                self.phase = "landed"
            elif self.continuous:
                self.phase = "motor_baseline"
        self._window()
        return fired

    def reward(self, identifier, value):
        if identifier not in self.records or self.brain.intervention != "intact":
            raise ValueError("Feedback needs a measured response with the intact circuit.")
        trace, post_counts = self.records[identifier]
        modulator_counts = np.zeros(self.brain.n, np.float32)
        self.brain.reset(64)
        index = next(i for i, j in enumerate(self.jobs) if j["id"] == identifier)
        for _ in range(12):
            self.senses.inject_odor(index)
            self.brain.v[self.plastic.modulators[value], 0] += .7
            modulator_counts[self.brain.step()] += 1
        gate = self.plastic.dopamine_gate(value, modulator_counts, post_counts)
        changed = self.plastic.reward(value, trace, edge_gate=gate)
        self.decoder.learn(identifier, self.features[identifier], value)
        self.last_reward = dict(sign=value, modulatorSpikes=int(modulator_counts[self.plastic.modulators[value]].sum()),
                                eligibleEdges=int(np.count_nonzero(gate)), changed=changed)
        return changed

    def depart(self):
        if self.landed:
            self.cooldowns[self.landed] = self.elapsed + 45
        self.attention = None
        self.new_round()

    def intervene(self, name):
        self.brain.intervene(name)
        self.turn = self.speed = self.brake = 0.
        self.new_round()
