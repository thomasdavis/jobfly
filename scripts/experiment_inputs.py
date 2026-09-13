"""Frozen public input vectors for reproducible brain experiments."""
import hashlib
import json
import os
from pathlib import Path
import numpy as np


def load_inputs():
    root = Path(os.getenv("JOBFLY_EXPERIMENT_INPUTS", Path(__file__).resolve().parents[1] / "docs/experiments"))
    meta = json.loads((root / "catalog.json").read_text())
    blob = root / "vectors.npz"
    if hashlib.sha256(blob.read_bytes()).hexdigest() != meta["vectorFileSHA256"]:
        raise ValueError("Experiment vector file checksum mismatch")
    with np.load(blob, allow_pickle=False) as data:
        vectors = data["vectors"].copy()
    if vectors.shape != (len(meta["jobs"]) + 1, 384) or not np.isfinite(vectors).all():
        raise ValueError("Experiment vector shape/content mismatch")
    if hashlib.sha256(vectors.tobytes()).hexdigest() != meta["vectorsSHA256"]:
        raise ValueError("Experiment vector content checksum mismatch")
    return meta, vectors
