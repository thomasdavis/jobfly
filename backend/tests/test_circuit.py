from types import SimpleNamespace
import numpy as np
import pytest
from backend.circuit import ActivityProjection, ActivityReadout
from backend.swarm import SwarmPolicy


def test_injected_neurons_cannot_manufacture_a_decision():
    brain = SimpleNamespace(n=6, cell_type=np.array(["ORN_A", "ORN_A", "KC", "KC", "MBON", "DN"]))
    projection = ActivityProjection(brain, np.array([0, 1]))
    features, energy = projection.encode(np.array([100, 100, 0, 0, 0, 0]))
    decoder = ActivityReadout()
    assert energy == 0
    assert decoder.predict(features) == 0
    assert decoder.learn("not-a-signal", features, 1) is False
    _, energy = projection.encode(np.array([0, 0, 2, 1, 1, 3]))
    assert energy > 0


def test_feedback_changes_measured_readout_and_survives_restore():
    positive = np.eye(512, dtype=np.float32)[0]
    negative = np.eye(512, dtype=np.float32)[1]
    readout = ActivityReadout()
    readout.learn("a", positive, 1)
    readout.learn("b", negative, -1)
    assert readout.predict(positive) > .8
    assert readout.predict(negative) < -.8
    restored = ActivityReadout()
    restored.restore(readout.samples)
    assert restored.predict(positive) == pytest.approx(readout.predict(positive))


def test_readout_resolves_similar_responses_with_opposite_feedback():
    positive = np.eye(512, dtype=np.float32)[0]
    negative = positive * .98 + np.eye(512, dtype=np.float32)[1] * .2
    negative /= np.linalg.norm(negative)
    readout = ActivityReadout()
    readout.learn("similar-a", positive, 1)
    readout.learn("similar-b", negative, -1)
    assert readout.predict(positive) > .8
    assert readout.predict(negative) < -.8


def test_shortlist_requires_time_and_several_flies_not_one_landing():
    swarm = object.__new__(SwarmPolicy)
    swarm.jobs = [{"id": "a"}, {"id": "b"}]
    swarm.decoder = ActivityReadout()
    feature = swarm.decoder.initial.copy()
    swarm.features = {"a": feature, "b": feature}
    swarm.active = 0
    swarm.observations = {
        "a": dict(visits=3, flies=[0, 1, 2], first=10, last=90, landings=0),
        "b": dict(visits=20, flies=[0], first=10, last=90, landings=20),
    }
    swarm.elapsed = 90
    assert swarm.summary()["recommendations"] == []
    swarm.elapsed = 150
    assert swarm.summary()["recommendations"] == ["a"]


def test_silenced_experiments_cannot_train_on_feedback():
    swarm = object.__new__(SwarmPolicy)
    swarm.brain = SimpleNamespace(intervention="no_wiring")
    with pytest.raises(ValueError, match="intact"):
        swarm.reward("a", 1)


def test_public_cache_removes_resume_context(tmp_path, monkeypatch):
    import hashlib
    import sqlite3
    from backend.senses import MODEL, cache_public_vectors, job_document
    path = tmp_path / "public.sqlite"
    monkeypatch.setenv("JOBFLY_JOB_VECTOR_CACHE", str(path))
    rng = np.random.default_rng(2)
    raw = rng.normal(size=(4, 384)).astype(np.float32)
    raw /= np.linalg.norm(raw, axis=1, keepdims=True)
    contextual = raw[:3] + .25 * raw[3]
    contextual /= np.linalg.norm(contextual, axis=1, keepdims=True)
    jobs = [dict(id=str(i), title=f"Public job {i}") for i in range(3)]
    cache_public_vectors(jobs, np.vstack([contextual, raw[3]]))
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT count(*) FROM vectors").fetchone()[0] == 3
        for i, job in enumerate(jobs):
            digest = hashlib.sha256((MODEL + job_document(job)).encode()).hexdigest()
            stored = np.frombuffer(db.execute("SELECT vector FROM vectors WHERE digest=?", (digest,)).fetchone()[0], np.float32)
            assert np.allclose(stored, raw[i], atol=1e-6)


def test_catalog_checkpoints_reuse_data_and_keep_legacy_history(tmp_path):
    import json
    from backend.storage import Store
    store = Store(tmp_path)
    jobs = [dict(id="a", title="Engineer", company="Employer")]
    # Existing pre-v3 snapshots still restore without migration or deletion.
    store.db.execute("INSERT INTO snapshots(payload) VALUES (?)", (json.dumps(dict(jobs=jobs, updates=0)),))
    store.db.commit()
    assert store.latest()["jobs"] == jobs
    for update in (1, 2, 3):
        store.save(dict(jobs=jobs, updates=update))
    assert store.latest()["jobs"] == jobs
    assert store.latest()["updates"] == 3
    assert store.db.execute("SELECT count(*) FROM objects").fetchone()[0] == 1
    assert store.db.execute("SELECT count(*) FROM snapshots").fetchone()[0] == 4
    store.db.close()


def test_nested_html_becomes_readable_text_before_neural_encoding():
    from backend.job_feed import plain_description
    assert plain_description("&lt;p&gt;Build &lt;strong&gt;great&lt;/strong&gt; software&lt;/p&gt;") == "Build  great  software"
    text = "C++ engineering, research & development."
    assert plain_description(plain_description(text)) == plain_description(text)
    text = "R&D, learning &growth; and AT&T."
    assert plain_description(text) == text
    assert plain_description(plain_description(text)) == text
