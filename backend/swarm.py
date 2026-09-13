"""24 independent continuous connectome simulations on one world clock."""
import math
import numpy as np
from .individual import Individual
from .learning import RewardPlasticity
from .motor import MotorDecoder
from .senses import Sensorium
from .checkpoint import pack, unpack


class SwarmPolicy:
    version = 4
    count = 24
    settle_seconds = 120

    def __init__(self, brain, plastic, jobs, vectors, samples=None, radius=8, saved=None):
        self.jobs, self.radius = jobs, radius
        self.rng = np.random.default_rng(390)
        self.elapsed = 0.
        self.steps = self.active = self.landings = self.updates = self.changed = 0
        self.observations = {}
        self.feedback_events = []
        self.checkpoint_due = False
        self.last_checkpoint = 0.
        # Fixed body calibration on a separate specimen, never job/user labels.
        self.motor_decoder = MotorDecoder(brain, Sensorium(brain, vectors), continuous=True)
        for value in vars(self.motor_decoder).values():
            if isinstance(value, np.ndarray):
                value.flags.writeable = False
        self.flies = []
        for i in range(self.count):
            own = brain.fork(10000 + i)
            fly = Individual(own, RewardPlasticity(own, anatomy=plastic), jobs, vectors, self.motor_decoder)
            angle = i * 2.399963
            r = radius * .8 * math.sqrt((i + .5) / self.count)
            fly.fly = dict(x=math.cos(angle) * r, z=math.sin(angle) * r, heading=angle)
            fly.radius = radius
            fly.sensory_gain = 1.
            self.flies.append(fly)
            self._round(fly)
            fly.phase = "warmup"
        if saved and saved.get("version") == self.version:
            state = unpack(saved["world"])
            self.rng.bit_generator.state = state.pop("rng")
            for key, value in state.items():
                setattr(self, key, value)
            if len(saved["flies"]) != self.count:
                raise ValueError("Incomplete individual-brain checkpoint")
            for fly, record in zip(self.flies, saved["flies"]):
                fly.restore(record)
            self.last_checkpoint = self.elapsed

    @property
    def brain(self):
        return self.flies[self.active].brain

    @property
    def plastic(self):
        return self.flies[self.active].plastic

    def __getattr__(self, name):
        flies = self.__dict__.get("flies")
        if not flies:
            raise AttributeError(name)
        return getattr(flies[self.active], name)

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
        measured = [i for i, j in enumerate(self.jobs) if j["id"] in self.observations]
        if measured:
            best = sorted(measured, key=lambda i: self.observations[self.jobs[i]["id"]].get("value", 0), reverse=True)[:12]
            recruited = int(self.rng.choice(best))
        else:
            recruited = int(self.rng.choice(available))
        fly.queue = list(dict.fromkeys([explore, local, recruited]))
        fly.moving_windows = 0

    def tick(self, learning=True, legacy_marks=None):
        if not self.jobs:
            return np.empty(0, np.int64)
        next_time = (self.steps + 1) * self.brain.dt
        packet = np.empty(0, np.int64)
        for i, fly in enumerate(self.flies):
            phase, index, old_rewards = fly.phase, fly.attending, fly.plastic.updates
            fired = fly.tick(learning)
            if i == self.active:
                packet = fired
            if phase == "comparing" and fly.window_step == 0 and index is not None:
                key = self.jobs[index]["id"]
                if key in fly.evidence and fly.evidence[key]["response"] > 1e-6:
                    item = self.observations.setdefault(key, dict(visits=0, flies=[], first=next_time, last=next_time, landings=0, values={}))
                    item["visits"] += 1
                    item["last"] = next_time
                    item["values"][str(i)] = fly.evidence[key]["value"]
                    item["value"] = float(np.mean(list(item["values"].values())))
                    if i not in item["flies"]:
                        item["flies"].append(i)
            if phase == "moving" and fly.window_step == 0:
                fly.moving_windows += 1
                if fly.landed:
                    self.landings += 1
                    if fly.landed in self.observations:
                        self.observations[fly.landed]["landings"] += 1
                    fly.dwell_until = next_time + 12
                elif fly.moving_windows >= 14:
                    self._round(fly)
            if fly.phase in ("landed", "no_response") and next_time >= fly.dwell_until:
                self._round(fly)
            if fly.plastic.updates != old_rewards:
                self.changed += fly.plastic.changed
                event = next(e for e in self.feedback_events if e["id"] == fly.last_reward["ticket"])
                event["completed"].append(i)
                event["changed"] += fly.plastic.changed
                self.checkpoint_due = True
                self._round(fly)
        self.steps += 1
        self.elapsed = next_time
        if self.elapsed - self.last_checkpoint >= 10:
            self.checkpoint_due = True
            self.last_checkpoint = self.elapsed
        return packet

    def public_flies(self):
        return [dict(id=i, **f.fly, phase=f.phase, target=self.jobs[f.target]["id"] if f.target is not None else None,
                     attending=self.jobs[f.attending]["id"] if f.attending is not None else None,
                     landed=f.landed, motor=[f.turn, f.speed, f.brake], active=i == self.active,
                     brainSteps=f.brain.steps, activeNeurons=int(f.brain.ever_active.sum()),
                     learningUpdates=f.plastic.updates, pendingFeedback=len(f.pending) + int(f.reward_ticket is not None))
                for i, f in enumerate(self.flies)]

    def summary(self):
        entries = {}
        for key, item in self.observations.items():
            mature = self.elapsed >= self.settle_seconds and self.elapsed - item["first"] >= 30 and len(item["flies"]) >= 3
            entries[key] = dict(visits=item["visits"], flies=len(item["flies"]), landings=item["landings"],
                                value=round(item.get("value", 0), 5), mature=mature)
        ranked = sorted((k for k in entries if entries[k]["mature"] and entries[k]["value"] > 0),
                        key=lambda k: entries[k]["value"], reverse=True)[:12]
        return dict(explored=len(entries), total=len(self.jobs), settling=self.elapsed < self.settle_seconds,
                    minimumSeconds=self.settle_seconds, recommendations=ranked, activity=entries,
                    activeFly=self.active, sharedBrain=False, independentBrains=self.count,
                    feedback=[dict(e) for e in self.feedback_events[-10:]])

    def checkpoint(self):
        return dict(version=self.version,
                    world=pack(dict(elapsed=self.elapsed, steps=self.steps, active=self.active,
                                    observations=self.observations, landings=self.landings, updates=self.updates,
                                    changed=self.changed, feedback_events=self.feedback_events,
                                    rng=self.rng.bit_generator.state)),
                    flies=[fly.checkpoint() for fly in self.flies])

    def reward(self, identifier, value):
        if self.brain.intervention != "intact":
            raise ValueError("Restore the intact circuit before teaching the swarm.")
        if not any(j["id"] == identifier for j in self.jobs):
            raise ValueError("Job not found.")
        self.updates += 1
        event = dict(id=self.updates, job=identifier, value=value, completed=[], changed=0)
        self.feedback_events.append(event)
        for fly in self.flies:
            fly.pending.append(dict(id=event["id"], job=identifier, value=value))
        self.checkpoint_due = True
        return 0  # Queued input; actual per-brain learning appears in telemetry.

    def focus(self, index):
        fly = self.flies[self.active]
        if fly.reward_ticket or fly.phase in ("warmup", "resume_baseline", "resume"):
            return
        self._round(fly)
        fly.queue = list(dict.fromkeys([index, *fly.queue]))[:3]
        fly.attention = index

    def depart(self):
        fly = self.flies[self.active]
        if not fly.reward_ticket:
            self._round(fly)

    def intervene(self, name):
        for fly in self.flies:
            fly.brain.intervene(name)
            # Discard a mixed-condition measurement, never neural state.
            fly.shadow = None
            fly._window()
            if fly.phase == "resume":
                fly.phase = "resume_baseline"
            elif fly.phase == "moving":
                fly.phase = "motor_baseline"
            if fly.phase == "reward":
                fly.reward_counts[:] = 0
                fly.reward_step = 0
            fly.turn = fly.speed = fly.brake = 0.
        self.observations.clear()
        self.checkpoint_due = True
