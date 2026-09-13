"""Small circuit fixtures test numerical/state contracts, not job accuracy."""
import copy
import json
import numpy as np
from scipy import sparse
from backend.circuit import CircuitBrain
from backend.learning import RewardPlasticity
from backend.swarm import SwarmPolicy


def circuit():
    b = object.__new__(CircuitBrain)
    b.n, b.batch, b.xp, b.device = 8, 1, np, "cpu"
    w = sparse.csc_matrix((np.array([.4, .2, -.3, .25, .2, .1], np.float32),
                           ([2, 2, 5, 2, 2, 0], [0, 1, 2, 3, 4, 7])), shape=(8, 8))
    b.indptr, b.indices, b.weights = w.indptr, w.indices, w.data
    b.cell_type = np.array(["KC-a", "KC-b", "MBON-a", "PAM-a", "PPL1-a", "DN", "LC10a", "ORN_A"])
    b.superclass = np.array(["central", "central", "central", "central", "central", "descending_neuron", "visual_projection", "sensory"])
    b.side = np.array(["L"] * 8)
    b.visual = b._visual = np.array([6])
    b.azimuth = np.array([-.5])
    b.positions = np.zeros((8, 3))
    b.groups = {}
    b.decay = np.float32(np.exp(-b.dt / b.tau))
    b.intervention = "intact"
    b.silenced = np.zeros(8, bool)
    b.ever_active = np.zeros(8, bool)
    b.last_active = np.empty(0, np.int64)
    b.reset(7)
    return b


def test_private_overlay_equals_an_explicit_weight_matrix():
    base = circuit()
    anatomy = RewardPlasticity(base)
    a, untouched = base.fork(12), base.fork(12)
    p = RewardPlasticity(a, anatomy=anatomy)
    before = untouched.weights.copy()
    p.reward(1, [1, .2])
    matrix = before.copy()
    matrix[p.edges] = p.original * p.factors
    explicit = copy.copy(untouched)
    explicit.weights = matrix
    del explicit.delta
    for fired in (np.array([0]), np.array([0, 1, 2]), np.arange(8)):
        np.testing.assert_allclose(a.synaptic_input(fired), explicit.synaptic_input(fired), atol=1e-7)
    assert np.array_equal(untouched.weights, before)
    assert untouched.delta is None
    assert not a.weights.flags.writeable


def test_perturbation_and_intervention_do_not_touch_other_brains():
    base = circuit()
    a, b = base.fork(91), base.fork(91)
    for _ in range(20):
        np.testing.assert_array_equal(a.step(), b.step())
    state = (b.v.copy(), b.fired.copy(), copy.deepcopy(b.rng.bit_generator.state), b.steps)
    a.v[0] += 100
    a.step()
    a.intervene("no_memory")
    np.testing.assert_array_equal(b.v, state[0])
    np.testing.assert_array_equal(b.fired, state[1])
    assert b.rng.bit_generator.state == state[2] and b.steps == state[3]
    assert b.intervention == "intact"


def make_swarm(saved=None):
    b = circuit()
    jobs = [dict(id="fixture", x=1., z=1.)]
    vectors = np.random.default_rng(4).normal(size=(2, 384)).astype(np.float32)
    return SwarmPolicy(b, RewardPlasticity(b), jobs, vectors, saved=saved)


def test_all_brains_advance_and_checkpoint_replays_mid_window(tmp_path):
    from backend.storage import Store
    a = make_swarm()
    for _ in range(245):
        a.tick()
    assert {f.brain.steps for f in a.flies} == {245}
    assert len({id(f.brain.rng) for f in a.flies}) == 24
    assert len({id(f.decoder) for f in a.flies}) == 24
    store = Store(tmp_path)
    store.save(dict(neural=dict(ecosystem=a.checkpoint())))
    b = make_swarm(store.latest()["neural"]["ecosystem"])
    assert all(f.shadow is not None for f in a.flies)
    for _ in range(39):
        a.tick()
        b.tick()
    assert json.dumps(a.checkpoint(), sort_keys=True) == json.dumps(b.checkpoint(), sort_keys=True)
    assert {f.brain.steps for f in a.flies} == {284}
    store.db.close()


def test_feedback_is_a_separate_input_to_each_individual():
    s = make_swarm()
    for _ in range(200):
        s.tick()
    voltage = [f.brain.v.copy() for f in s.flies]
    assert s.reward("fixture", 1) == 0
    for fly, old in zip(s.flies, voltage):
        np.testing.assert_array_equal(fly.brain.v, old)
        assert fly.plastic.updates == 0 and len(fly.pending) == 1
    assert len({id(f.pending[0]) for f in s.flies}) == 24
    restored = make_swarm(s.checkpoint())
    for _ in range(160):
        s.tick()
        restored.tick()
    assert json.dumps(s.checkpoint(), sort_keys=True) == json.dumps(restored.checkpoint(), sort_keys=True)
    assert {f.brain.steps for f in s.flies} == {360}
    assert {f.plastic.updates for f in s.flies} == {1}
    assert sorted(s.feedback_events[0]["completed"]) == list(range(24))
    assert len({id(f.plastic.factors) for f in s.flies}) == 24


def test_disconnected_circuit_has_no_stimulus_response_but_keeps_ticking():
    s = make_swarm()
    s.intervene("no_wiring")
    for _ in range(400):
        s.tick()
    assert {f.brain.steps for f in s.flies} == {400}
    assert s.summary()["explored"] == 0
    assert all(not f.evidence or all(e["response"] == 0 for e in f.evidence.values()) for f in s.flies)
