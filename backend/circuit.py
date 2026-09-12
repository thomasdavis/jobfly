"""Whole-connectome activity, causal interventions, and activity-only readouts."""
import numpy as np

from .vendor.fly_ai.fly_brain import FlyBrain

INTERVENTIONS = ("intact", "no_wiring", "no_smell", "no_memory", "no_vision", "no_motor")


class CircuitBrain(FlyBrain):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.intervention = "intact"
        self.silenced = np.zeros(self.n, bool)
        self.ever_active = np.zeros(self.n, bool)
        self.last_active = np.empty(0, np.int64)

    def intervene(self, name):
        if name not in INTERVENTIONS:
            raise ValueError("Unknown circuit intervention.")
        self.intervention = name
        self.silenced[:] = False
        if name == "no_smell":
            self.silenced = np.char.startswith(self.cell_type, "ORN_")
        elif name == "no_memory":
            self.silenced = np.char.startswith(self.cell_type, "KC") | np.char.startswith(self.cell_type, "MBON")
        elif name == "no_vision":
            self.silenced = np.isin(self.superclass, ["ol_sensory", "ol_intrinsic", "visual_projection", "visual_centrifugal"])
        elif name == "no_motor":
            self.silenced = np.isin(self.superclass, ["descending_neuron", "vnc_motor", "cb_motor"])
        self.reset(64)

    def synaptic_input(self, fired):
        if self.intervention == "no_wiring":
            return np.zeros_like(self.v)
        return super().synaptic_input(fired)

    def step(self, **kwargs):
        self.v[self.silenced] = 0
        if len(self.fired):
            self.fired = self.fired[~self.silenced[self.fired]]
        fired = super().step(**kwargs)
        self.fired = fired[~self.silenced[fired]]
        self.v[self.silenced] = 0
        self.ever_active[self.fired] = True
        self.last_active = self.fired
        return self.fired


class ActivityProjection:
    """Every non-injected neuron contributes through its annotated population.

    Fixed signed hashing compresses population response into 512 measurements.
    The readout cannot inspect text, embeddings, synaptic factors, or job IDs.
    """
    size = 512

    def __init__(self, brain, driven):
        _, self.population = np.unique(brain.cell_type, return_inverse=True)
        self.allowed = np.ones(brain.n, bool)
        self.allowed[driven] = False
        self.population_size = np.maximum(np.bincount(self.population, weights=self.allowed), 1)
        rng = np.random.default_rng(904)
        count = len(self.population_size)
        self.buckets = rng.integers(self.size, size=(2, count))
        self.signs = rng.choice([-1., 1.], size=(2, count))

    def encode(self, response):
        values = np.bincount(self.population, weights=response * self.allowed,
                             minlength=len(self.population_size)) / np.sqrt(self.population_size)
        result = sum(np.bincount(bucket, weights=values * sign, minlength=self.size)
                     for bucket, sign in zip(self.buckets, self.signs))
        norm = np.linalg.norm(result)
        return (result / max(norm, 1e-8)).astype(np.float32), float(norm)


class ActivityReadout:
    """Regularized decoder trained only on actual neural-response measurements.

    The artificial decoder is explicit. This is reservoir computing, not a claim
    that unmodified fly neurons understand careers or human reward semantics.
    """
    def __init__(self):
        self.samples = {}
        self.matrix = np.empty((0, ActivityProjection.size), np.float32)
        self.alpha = np.empty(0)
        self.bandwidth = .025
        rng = np.random.default_rng(845)
        self.initial = rng.normal(size=ActivityProjection.size)
        self.initial /= np.linalg.norm(self.initial)

    def fit(self):
        rows = list(self.samples.values())
        if not rows:
            self.matrix = np.empty((0, ActivityProjection.size), np.float32)
            self.alpha = np.empty(0)
            return
        self.matrix = np.asarray([r[0] for r in rows], np.float32)
        distance = np.maximum(0, 1 - self.matrix @ self.matrix.T)
        distinct = distance[np.triu_indices(len(rows), 1)]
        distinct = distinct[distinct > 1e-6]
        self.bandwidth = max(float(np.median(distinct)), 1e-5) if len(distinct) else .025
        kernel = np.exp(-distance / self.bandwidth)
        self.alpha = np.linalg.solve(kernel + np.eye(len(rows)) * .08,
                                     np.array([r[1] for r in rows]))

    def learn(self, key, features, reward):
        if np.linalg.norm(features) < 1e-6:
            return False
        self.samples[key] = (np.asarray(features, np.float32).tolist(), int(reward))
        if len(self.samples) > 128:
            del self.samples[next(iter(self.samples))]
        self.fit()
        return True

    def predict(self, features):
        if np.linalg.norm(features) < 1e-6:
            return 0.
        if not len(self.matrix):
            return float(features @ self.initial) * .25
        k = np.exp(-np.maximum(0, 1 - self.matrix @ features) / self.bandwidth)
        return float(np.clip(k @ self.alpha, -1.5, 1.5))

    def restore(self, samples):
        for key, (features, reward) in samples.items():
            x = np.asarray(features, np.float32)
            if x.shape != (ActivityProjection.size,) or not np.isfinite(x).all() or reward not in (-1, 1):
                raise ValueError("Saved neural decoder is invalid.")
            self.samples[key] = (x.tolist(), reward)
        self.fit()
