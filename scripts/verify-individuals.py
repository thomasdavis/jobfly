"""Full MaleCNS experiment; inputs are frozen, source-linked real jobs."""
import hashlib
import json
import os
import resource
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("FLY_DATA", "/mnt/donto-data/donto-resources/research/jobfly-runtime/brain")
os.environ.setdefault("NUMBA_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np
from backend.circuit import CircuitBrain
from backend.learning import RewardPlasticity
from backend.storage import Store
from backend.swarm import SwarmPolicy

root = Path("/mnt/donto-data/donto-resources/research/jobfly-independent-v4")
root.mkdir(parents=True, exist_ok=True)
store = Store(Path("/mnt/donto-data/donto-resources/research/jobfly-neural-v2/integration-state"))
data = store.latest()
store.db.close()
jobs = data["jobs"]
vectors = np.asarray(data["neural"]["vectors"], np.float32)
assert len(jobs) > 1000 and all(j.get("url", "").startswith("http") for j in jobs)
source_hashes = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in Path("backend").glob("*.py")}
start = time.monotonic()
brain = CircuitBrain(device="cpu")
plastic = RewardPlasticity(brain)
print("Loaded full circuit", brain.n, len(brain.weights), flush=True)
swarm = SwarmPolicy(brain, plastic, jobs, vectors, radius=45)
print("24 brains constructed", round(time.monotonic() - start), swarm.motor_decoder.calibration, flush=True)
assert len({id(f.brain.v) for f in swarm.flies}) == 24
assert len({id(f.brain.rng) for f in swarm.flies}) == 24
assert len({id(f.decoder) for f in swarm.flies}) == 24
assert len({id(f.plastic.factors) for f in swarm.flies}) == 24
initial = swarm.public_flies()
limit = int(os.getenv("JOBFLY_EXPERIMENT_STEPS", "7000"))
for tick in range(limit):
    swarm.tick()
    assert all(f.brain.steps == tick + 1 for f in swarm.flies)
    if (tick + 1) % 100 == 0:
        summary = swarm.summary()
        moved = sum(np.hypot(f.fly["x"] - p["x"], f.fly["z"] - p["z"]) > .01 for f, p in zip(swarm.flies, initial))
        report = dict(steps=tick + 1, elapsed=swarm.elapsed, wallSeconds=round(time.monotonic() - start, 2),
                      maxRSSMB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
                      sourceHashes=source_hashes, jobs=len(jobs), moved=int(moved), landings=swarm.landings, explored=summary["explored"],
                      recommendations=summary["recommendations"], ratings=swarm.updates,
                      uniqueVoltages=len({hashlib.sha256(f.brain.v.tobytes()).hexdigest() for f in swarm.flies}),
                      flies=swarm.public_flies())
        (root / "progress.json").write_text(json.dumps(report, indent=2))
        print({k: v for k, v in report.items() if k not in ("flies", "sourceHashes")}, flush=True)
        if summary["recommendations"] and moved == 24 and swarm.landings:
            break
assert moved == 24
assert swarm.summary()["recommendations"] and swarm.updates == 0
(root / "autonomous.json").write_text(json.dumps(report, indent=2))
# Save exact pre-feedback state for independent reproducibility and replay tests.
checkpoint = swarm.checkpoint()
out = Store(root / "experiment-state")
out.save(dict(jobs=jobs, resume=data["resume"], marks={}, reasons={}, source=data["source"],
              neural=dict(vectors=vectors.tolist(), ecosystem=checkpoint)))
out.db.close()
print("AUTONOMOUS PASS; checkpoint saved", flush=True)
