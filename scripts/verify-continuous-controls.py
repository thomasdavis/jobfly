"""Predeclared numerical and held-out controls; no job-quality claims."""
import copy
import hashlib
import json
import os
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("FLY_DATA", "/mnt/donto-data/donto-resources/research/jobfly-runtime/brain")
os.environ.setdefault("NUMBA_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np
from backend.circuit import CircuitBrain, ActivityProjection
from backend.learning import RewardPlasticity
from backend.motor import MotorDecoder, measure, paired_measure
from backend.senses import Sensorium
from backend.storage import Store

root = Path("/mnt/donto-data/donto-resources/research/jobfly-independent-v4")
root.mkdir(parents=True, exist_ok=True)
store = Store(Path("/mnt/donto-data/donto-resources/research/jobfly-neural-v2/integration-state"))
saved = store.latest()
store.db.close()
vectors = np.asarray(saved["neural"]["vectors"], np.float32)
source_hashes = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in Path("backend").glob("*.py")}
b = CircuitBrain(device="cpu")
p = RewardPlasticity(b)
motor = MotorDecoder(b, Sensorium(b, vectors), continuous=True)
report = dict(protocol="continuous-v4", neurons=b.n, connections=len(b.weights), calibration=motor.calibration)
# Independent trials; never resetting between baseline and visual stimulation.
movement = []
for seed in (301, 509, 701):
    trial = b.fork(seed)
    senses = Sensorium(trial, vectors)
    measure(trial, senses, steps=128, reset=False)
    for direction in (-.9, -.6, -.2, .2, .6, .9):
        measure(trial, senses, reset=False)
        response, baseline = paired_measure(trial, senses, direction, intensity=1.1)
        turn, speed, brake = motor.decode(response, baseline)
        movement.append(dict(seed=seed, direction=direction, turn=turn, speed=speed, brake=brake,
                             correctSign=bool(turn * direction > 0)))
report["heldoutMovement"] = movement
print("Held-out movement", sum(x["correctSign"] for x in movement), "/", len(movement), flush=True)
(root / "controls.json").write_text(json.dumps(report, indent=2))

# Paired counterfactuals start from exactly the same mature state and RNG.
# Only the intervention/stimulus differs; directly injected neurons are excluded.
responses = []
for seed in (301, 509, 701):
    warm = b.fork(seed)
    measure(warm, Sensorium(warm, vectors), steps=128, reset=False)
    for intervention in ("intact", "no_wiring", "no_smell", "no_memory"):
        for job in range(4):
            pair = []
            for odor in (False, True):
                trial = b.fork(seed)
                trial.v[:] = warm.v
                trial.fired = warm.fired.copy()
                trial.rng.bit_generator.state = copy.deepcopy(warm.rng.bit_generator.state)
                trial.intervene(intervention)
                senses = Sensorium(trial, vectors)
                counts = np.zeros(trial.n, np.float32)
                for _ in range(32):
                    if odor:
                        senses.inject_odor(job)
                    counts[trial.step()] += 1
                pair.append(counts)
            features, energy = ActivityProjection(trial, senses.driven).encode(pair[1] - pair[0])
            responses.append(dict(seed=seed, intervention=intervention, job=job, response=energy))
    print("Counterfactual seed", seed, flush=True)
report["pairedResponses"] = responses
assert all(x["response"] == 0 for x in responses if x["intervention"] in ("no_wiring", "no_smell"))
assert all(x["response"] > 0 for x in responses if x["intervention"] == "intact")

# Sparse-overlay current equals explicit full-weight copy for actual model edges.
private = b.fork(909)
own = RewardPlasticity(private, anatomy=p)
own.reward(1, np.ones(len(own.kc)))
explicit = b.fork(909)
explicit.weights = b.weights.copy()
explicit.weights[own.edges] = own.original * own.factors
currents = []
for seed in (4, 9, 22):
    fired = np.random.default_rng(seed).choice(b.n, size=10000, replace=False)
    a, c = private.synaptic_input(fired), explicit.synaptic_input(fired)
    error = float(np.max(np.abs(a-c)))
    np.testing.assert_allclose(a, c, atol=1e-6, rtol=1e-5)
    currents.append(error)
report["overlayMaxCurrentError"] = currents
report["baseWeightsUnmodified"] = bool(not b.weights.flags.writeable)
report["sourceHashes"] = source_hashes
(root / "controls.json").write_text(json.dumps(report, indent=2))
print("CONTROL PASS", flush=True)
