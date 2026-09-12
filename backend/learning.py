"""Bounded, replayable reward plasticity on existing KC → MBON edges.

This is an engineered learning rule, not a validated dopamine model.
No edges are added. Original weights and transmitter signs are preserved.
"""
import numpy as np


class RewardPlasticity:
    def __init__(self, brain):
        self.brain = brain
        self.kc = np.flatnonzero(np.char.startswith(brain.cell_type, "KC"))
        self.mbon = np.flatnonzero(np.char.startswith(brain.cell_type, "MBON"))
        if not len(self.kc) or not len(self.mbon):
            raise ValueError("Connectome is missing KC or MBON annotations.")
        edges, owners = [], []
        targets = set(self.mbon.tolist())
        for owner, neuron in enumerate(self.kc):
            start, end = brain.indptr[neuron:neuron+2]
            for edge in range(start, end):
                if int(brain.indices[edge]) in targets:
                    edges.append(edge)
                    owners.append(owner)
        self.edges = np.asarray(edges, dtype=np.int32)
        self.owners = np.asarray(owners, dtype=np.int32)
        self.original = brain.weights[self.edges].copy()
        self.factors = np.ones(len(self.edges), dtype=np.float32)
        self.eligibility = np.zeros(len(self.kc), dtype=np.float32)
        self.updates = 0
        self.changed = 0
        if not len(edges):
            raise ValueError("No KC → MBON edges resolved; learning cannot start.")

    def observe(self, fired):
        self.eligibility *= .96
        self.eligibility += np.isin(self.kc, fired).astype(np.float32) * .04

    def reward(self, value, trace):
        active = np.asarray(trace, dtype=np.float32)
        active = np.clip(active / max(float(active.max()), 1e-6), 0, 1)
        previous = self.factors.copy()
        self.factors = np.clip(self.factors + .22 * value * active[self.owners], .25, 2)
        self.brain.weights[self.edges] = self.original * self.factors
        self.changed = int(np.count_nonzero(np.abs(self.factors - previous) > 1e-7))
        self.updates += 1
        return self.changed

    def preference(self, code):
        # Project the modified circuit strengths into an attraction signal.
        # This explicit adapter is distinct from the downstream motor simulation.
        active = code[self.owners]
        return float(np.sum((self.factors - 1) * active) / max(float(active.sum()), 1))

    def restore(self, factors, updates):
        factors = np.asarray(factors, dtype=np.float32)
        if factors.shape != self.factors.shape or not np.isfinite(factors).all():
            raise ValueError("Saved plasticity does not match this connectome.")
        self.factors = np.clip(factors, .25, 2)
        self.brain.weights[self.edges] = self.original * self.factors
        self.updates = updates
