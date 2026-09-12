from types import SimpleNamespace

import numpy as np
from scipy import sparse

from backend.jobs import SensoryEncoder
from backend.learning import RewardPlasticity
from backend.storage import Store


def tiny_brain():
    # Two KC → MBON edges and an unrelated inhibitory motor connection.
    matrix = sparse.csc_matrix(([.4, .2, -.3], ([2, 2, 3], [0, 1, 2])), shape=(4, 4))
    return SimpleNamespace(cell_type=np.array(["KC-a", "KC-b", "MBON-a", "DNa02"]),
                           indptr=matrix.indptr, indices=matrix.indices, weights=matrix.data)


def test_reward_changes_only_eligible_existing_edges():
    brain = tiny_brain()
    plastic = RewardPlasticity(brain)
    original = brain.weights.copy()
    assert plastic.reward(1, [1, 0]) == 1
    assert brain.weights[0] > original[0]
    assert np.array_equal(brain.weights[1:], original[1:])
    assert plastic.preference(np.array([1, 0])) > plastic.preference(np.array([0, 1]))


def test_negative_reward_bounds_and_signs():
    brain = tiny_brain()
    plastic = RewardPlasticity(brain)
    for _ in range(100):
        plastic.reward(-1, [1, 0])
    assert np.isclose(plastic.factors[0], .25)
    assert brain.weights[0] > 0
    assert brain.weights[2] == -.3


def test_restore_reproduces_synapses_and_preference(tmp_path):
    a = RewardPlasticity(tiny_brain())
    a.reward(1, [1, .2])
    store = Store(tmp_path)
    payload = dict(factors=a.factors.tolist(), updates=a.updates)
    store.save(payload, ("job-1", 1, "Interesting", a.changed))
    b = RewardPlasticity(tiny_brain())
    saved = Store(tmp_path).latest()
    b.restore(saved["factors"], saved["updates"])
    assert np.array_equal(a.brain.weights, b.brain.weights)
    assert len(store.history()) == 1
    store.save({**payload, "updates": 2})
    assert store.db.execute("SELECT count(*) FROM snapshots").fetchone()[0] == 2


def test_sensory_identity_survives_corpus_change():
    jobs = [{"id": str(i), "title": f"Role {i}", "description": text} for i, text in enumerate(["React web interfaces", "Python data pipelines", "Rust platform services"])]
    before = SensoryEncoder(jobs[:2], 128)
    after = SensoryEncoder(jobs, 128)
    assert np.array_equal(before.codes[0], after.codes[0])
    assert not np.array_equal(after.codes[0], after.codes[-1])


def test_zero_activity_is_not_rewarded():
    plastic = RewardPlasticity(tiny_brain())
    assert plastic.reward(1, [0, 0]) == 0
    assert np.all(plastic.factors == 1)
