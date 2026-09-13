"""Bounded, replayable reward plasticity on existing KC → MBON edges.

This is an engineered learning rule, not a validated dopamine model.
No edges are added. Original weights and transmitter signs are preserved.
"""
import numpy as np


class RewardPlasticity:
    def __init__(self, brain, anatomy=None):
        self.brain = brain
        if anatomy is not None:
            for name in ("kc", "mbon", "edges", "owners", "posts", "original", "modulators"):
                setattr(self, name, getattr(anatomy, name))
            self.factors = np.ones(len(self.edges), np.float32)
            self.eligibility = np.zeros(len(self.kc), np.float32)
            self.updates = self.changed = 0
            return
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
        self.posts = brain.indices[self.edges]
        self.original = brain.weights[self.edges].copy()
        self.factors = np.ones(len(self.edges), dtype=np.float32)
        self.eligibility = np.zeros(len(self.kc), dtype=np.float32)
        self.updates = 0
        self.changed = 0
        self.modulators = {
            1: np.flatnonzero(np.char.startswith(brain.cell_type, "PAM")),
            -1: np.flatnonzero(np.char.startswith(brain.cell_type, "PPL1")),
        }
        if not len(edges):
            raise ValueError("No KC → MBON edges resolved; learning cannot start.")

    def _apply(self):
        values = self.original * self.factors
        if hasattr(self.brain, "set_plastic_weights"):
            self.brain.set_plastic_weights(self.edges, values)
        else:
            self.brain.weights[self.edges] = values

    def observe(self, fired):
        self.eligibility *= .96
        self.eligibility += np.isin(self.kc, fired).astype(np.float32) * .04

    def reward(self, value, trace, edge_gate=None):
        active = np.asarray(trace, dtype=np.float32)
        active = np.clip(active / max(float(active.max()), 1e-6), 0, 1)
        previous = self.factors.copy()
        eligibility = active[self.owners]
        if edge_gate is not None:
            gate = np.asarray(edge_gate, dtype=np.float32)
            if gate.shape != self.edges.shape or not np.isfinite(gate).all():
                raise ValueError("Invalid reward gate.")
            eligibility *= np.clip(gate, 0, 1)
        self.factors = np.clip(self.factors + .22 * value * eligibility, .25, 2)
        self._apply()
        self.changed = int(np.count_nonzero(np.abs(self.factors - previous) > 1e-7))
        self.updates += 1
        return self.changed

    def dopamine_gate(self, value, modulator_counts, post_counts):
        """Actual DAN activity × its measured outgoing connectivity × MBON activity.

        This is an engineered three-factor rule. The anatomical matrix does not
        identify dopamine receptors or validate the sign of biological plasticity.
        """
        reach = np.zeros(self.brain.n, np.float32)
        for neuron in self.modulators[value]:
            start, end = self.brain.indptr[neuron:neuron+2]
            np.add.at(reach, self.brain.indices[start:end],
                      np.abs(self.brain.weights[start:end]) * modulator_counts[neuron])
        gate = reach[self.posts] * np.maximum(post_counts[self.posts], 0)
        return gate / max(float(gate.max()), 1e-8)

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
        self._apply()
        self.updates = updates
