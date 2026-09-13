"""One continuously integrated brain, body and independently learned readout."""
import numpy as np
from .policy import NeuralPolicy
from .motor import STEPS
from .checkpoint import pack, unpack


class Individual(NeuralPolicy):
    def __init__(self, brain, plastic, jobs, vectors, motor):
        super().__init__(brain, plastic, jobs, vectors, motor=motor, continuous=True)
        self.shadow = None
        self.null_counts = np.zeros(brain.n, np.float32)
        self.phase = "warmup"
        self.pending = []
        self.reward_ticket = None
        self.reward_counts = np.zeros(brain.n, np.float32)
        self.reward_step = 0
        self.dwell_until = 0.
        self.moving_windows = 0

    def tick(self, learning=True, legacy_marks=None):
        # Feedback is an input event, delivered separately to every individual.
        # Nobody receives another fly's fitted decoder or synaptic update.
        if (self.pending and self.reward_ticket is None and self.window_step == 0
                and self.phase not in ("warmup", "resume_baseline", "resume")
                and learning and self.brain.intervention == "intact"):
            self.reward_ticket = self.pending.pop(0)
            index = next(i for i, j in enumerate(self.jobs) if j["id"] == self.reward_ticket["job"])
            self.new_round()
            self.queue = [index]
        if self.phase in ("warmup", "resume_baseline", "resume"):
            if self.phase == "resume":
                if self.window_step == 0:
                    self.shadow = self.brain.counterfactual()
                    self.null_counts[:] = 0
                self.null_counts[self.shadow.step()] += 1
                self.senses.inject_odor(len(self.jobs))
            fired = self.brain.step()
            self.counts[fired] += 1
            self.window_step += 1
            self.elapsed += self.brain.dt
            limit = 128 if self.phase == "warmup" else STEPS
            if self.window_step == limit:
                if self.phase == "warmup":
                    self.phase = "resume_baseline"
                elif self.phase == "resume_baseline":
                    self.baseline = self.counts.copy()
                    self.phase = "resume"
                else:
                    self.decoder.initial = self.project.encode(self.counts - self.null_counts)[0]
                    self.phase = "baseline"
                    self.shadow = None
                self._window()
            return fired
        if self.phase == "reward":
            enabled = learning and self.brain.intervention == "intact"
            if enabled:
                ticket = self.reward_ticket
                index = next(i for i, j in enumerate(self.jobs) if j["id"] == ticket["job"])
                self.senses.inject_odor(index)
                self.brain.v[self.plastic.modulators[ticket["value"]], 0] += .7
            fired = self.brain.step()
            self.elapsed += self.brain.dt
            if enabled:
                self.reward_counts[fired] += 1
                self.reward_step += 1
                if self.reward_step == 12:
                    trace, post = self.records[ticket["job"]]
                    gate = self.plastic.dopamine_gate(ticket["value"], self.reward_counts, post)
                    changed = self.plastic.reward(ticket["value"], trace, edge_gate=gate)
                    self.decoder.learn(ticket["job"], self.features[ticket["job"]], ticket["value"])
                    self.last_reward = dict(ticket=ticket["id"], sign=ticket["value"], changed=changed,
                                            modulatorSpikes=int(self.reward_counts[self.plastic.modulators[ticket["value"]]].sum()))
                    self.reward_ticket = None
                    self.new_round()
            return fired
        if self.phase in ("landed", "no_response"):
            # Even resting bodies have active brains and advancing noise streams.
            fired = self.brain.step()
            self.elapsed += self.brain.dt
            return fired
        old_phase, key = self.phase, self.attending
        if self.phase in ("comparing", "moving"):
            if self.window_step == 0:
                self.shadow = self.brain.counterfactual()
                self.null_counts[:] = 0
            self.null_counts[self.shadow.step()] += 1
            if self.window_step == STEPS - 1:
                self.baseline = self.null_counts.copy()
        fired = super().tick(learning=False)
        if self.window_step == 0:
            self.shadow = None
        if old_phase == "comparing" and self.window_step == 0 and self.reward_ticket:
            assert self.jobs[key]["id"] == self.reward_ticket["job"]
            self.phase = "reward"
            self.reward_counts[:] = 0
            self.reward_step = 0
        return fired

    def checkpoint(self):
        excluded = {"brain", "plastic", "jobs", "senses", "project", "decoder", "motor_decoder", "shadow"}
        return pack(dict(shadow=None if self.shadow is None else dict(v=self.shadow.v, fired=self.shadow.fired, steps=self.shadow.steps, rng=self.shadow.rng.bit_generator.state, ever_active=self.shadow.ever_active), policy={k: v for k, v in vars(self).items() if k not in excluded},
                         brain=dict(v=self.brain.v, fired=self.brain.fired, steps=self.brain.steps,
                                    rng=self.brain.rng.bit_generator.state, ever_active=self.brain.ever_active,
                                    intervention=self.brain.intervention, silenced=self.brain.silenced),
                         plastic=dict(factors=self.plastic.factors, updates=self.plastic.updates,
                                      changed=self.plastic.changed, eligibility=self.plastic.eligibility),
                         decoder=dict(samples=self.decoder.samples, initial=self.decoder.initial)))

    def restore(self, checkpoint):
        state = unpack(checkpoint)
        if state["brain"]["v"].shape != self.brain.v.shape:
            raise ValueError("Checkpoint does not match this brain")
        self.__dict__.update(state["policy"])
        for key, value in state["brain"].items():
            if key == "rng":
                self.brain.rng.bit_generator.state = value
            else:
                setattr(self.brain, key, value)
        self.brain.last_active = self.brain.fired
        self.plastic.restore(state["plastic"]["factors"], state["plastic"]["updates"])
        self.shadow = None
        if state.get("shadow") is not None:
            self.shadow = self.brain.counterfactual()
            for key, value in state["shadow"].items():
                if key == "rng":
                    self.shadow.rng.bit_generator.state = value
                else:
                    setattr(self.shadow, key, value)
        self.plastic.restore(state["plastic"]["factors"], state["plastic"]["updates"])
        self.plastic.changed = state["plastic"]["changed"]
        self.plastic.eligibility = state["plastic"]["eligibility"]
        self.decoder.initial = state["decoder"]["initial"]
        self.decoder.restore(state["decoder"]["samples"])
