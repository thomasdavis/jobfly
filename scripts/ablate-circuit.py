"""Paired full-model interventions; no visitor sessions are touched."""
import os
import sys
import json
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("NUMBA_NUM_THREADS", "2")
import numpy as np
from backend.engine import Engine
from backend.storage import Store
from backend.motor import measure, STEPS
from backend.circuit import INTERVENTIONS

root = Path("/mnt/donto-data/donto-resources/research/jobfly-neural-v2")
source = Store(root / "integration-state")
copy = Store(root / "ablation-state")
copy.save(source.latest())
source.db.close()
copy.db.close()
engine = Engine(root / "ablation-state")
while engine.status == "loading":
    time.sleep(1)
assert engine.status == "ready", engine.error
engine.stopped = True
engine.thread.join(timeout=3)
brain, policy = engine.brain, engine.policy
results = {}
for mode in INTERVENTIONS:
    brain.intervene(mode)
    baseline = measure(brain, policy.senses)
    features, energies = [], []
    for i in range(8):
        brain.reset(64)
        counts = np.zeros(brain.n, np.float32)
        for _ in range(STEPS):
            policy.senses.inject_odor(i)
            counts[brain.step()] += 1
        feature, energy = policy.project.encode(counts - baseline)
        features.append(feature)
        energies.append(energy)
    motor = policy.motor_decoder.decode(measure(brain, policy.senses, .45), baseline)
    array = np.asarray(features)
    results[mode] = dict(meanResponse=float(np.mean(energies)), individualResponse=energies,
                         motor=motor, features=array.tolist())
    print(mode, results[mode]["meanResponse"], motor, flush=True)
intact = np.asarray(results["intact"]["features"])
for row in results.values():
    features = np.asarray(row.pop("features"))
    row["responseDistanceFromIntact"] = float(np.linalg.norm(features-intact, axis=1).mean())
assert results["no_wiring"]["meanResponse"] == 0
assert results["no_smell"]["meanResponse"] == 0
assert all(abs(v) < 1e-8 for v in results["no_motor"]["motor"])
assert all(abs(v) < 1e-8 for v in results["no_vision"]["motor"])
assert results["intact"]["meanResponse"] > 0
(root / "ablation.json").write_text(json.dumps(results, indent=2))
engine.store.db.close()
