"""Read-only complete-network calibration probe; writes no visitor state."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("FLY_DATA", "/mnt/donto-data/donto-resources/research/jobfly-runtime/brain")
os.environ.setdefault("NUMBA_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import numpy as np
from backend.circuit import CircuitBrain, ActivityProjection
from backend.senses import Sensorium
from backend.motor import MotorDecoder, measure

brain = CircuitBrain(device="cpu")
vectors = np.random.default_rng(5).normal(size=(3, 384)).astype(np.float32)
vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
senses = Sensorium(brain, vectors)
motor = MotorDecoder(brain, senses)
rows = []
for direction in [-.85, -.45, -.15, .15, .45, .85]:
    counts = measure(brain, senses, direction)
    turn, speed, brake = motor.decode(counts)
    row = dict(direction=direction, turn=turn, speed=speed, brake=brake)
    rows.append(row)
    print(row, flush=True)
report = dict(calibration=motor.calibration, heldOut=rows)
out = Path('/mnt/donto-data/donto-resources/research/jobfly-neural-v2/motor-probe.json')
out.write_text(json.dumps(report, indent=2))
print(report['calibration'])
