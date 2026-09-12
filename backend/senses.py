"""Semantic text → artificial receptor patterns; no job scores leave this module."""
import json
import os
import threading
import hashlib
import sqlite3
from pathlib import Path

import numpy as np

MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_model = None
_lock = threading.Lock()


def job_document(job):
    return "\n".join(str(job.get(k) or "") for k in ("title", "company", "description", "skills", "location", "salary", "interpretation"))


def cache_public_vectors(jobs, contextual):
    """Recover unit job vectors from v3 checkpoints to warm the public cache.

    y = normalize(j + .25*r), with ||j||=||r||=1. Solving the positive
    quadratic for its norm exactly removes the private resume contribution.
    Only the recovered public job vector is cached, never r or the checkpoint.
    """
    if contextual.shape != (len(jobs) + 1, 384):
        return
    r, y = contextual[-1], contextual[:-1]
    t = y @ r
    raw = y * (.25 * t + np.sqrt(.9375 + .0625 * t * t))[:, None] - .25 * r
    raw /= np.maximum(np.linalg.norm(raw, axis=1, keepdims=True), 1e-8)
    path = Path(os.getenv("JOBFLY_JOB_VECTOR_CACHE", "/mnt/donto-data/donto-resources/research/jobfly-runtime/job-vectors.sqlite"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as cache:
        cache.execute("CREATE TABLE IF NOT EXISTS vectors (digest TEXT PRIMARY KEY, vector BLOB NOT NULL)")
        for job, vector in zip(jobs, raw):
            digest = hashlib.sha256((MODEL + job_document(job)).encode()).hexdigest()
            cache.execute("INSERT OR IGNORE INTO vectors VALUES (?,?)", (digest, vector.astype(np.float32).tobytes()))


def semantic_vectors(jobs, resume, progress=None):
    global _model
    if not jobs:
        return np.empty((0, 384), np.float32)
    with _lock:
        if _model is None:
            from fastembed import TextEmbedding
            _model = TextEmbedding(model_name=MODEL, threads=1,
                                   cache_dir=os.getenv("JOBFLY_EMBED_CACHE", "/mnt/donto-data/donto-resources/research/jobfly-runtime/embeddings"),
                                   local_files_only=True)
        # Chunk long documents instead of silently embedding only their opening.
        documents = [json.dumps(resume or {}, ensure_ascii=False)] + [job_document(j) for j in jobs]
        cache_path = Path(os.getenv("JOBFLY_JOB_VECTOR_CACHE", "/mnt/donto-data/donto-resources/research/jobfly-runtime/job-vectors.sqlite"))
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache = sqlite3.connect(cache_path)
        cache.execute("CREATE TABLE IF NOT EXISTS vectors (digest TEXT PRIMARY KEY, vector BLOB NOT NULL)")
        vectors = np.zeros((len(documents), 384), np.float32)
        chunks, owners, missing = [], [], []
        for owner, text in enumerate(documents):
            digest = hashlib.sha256((MODEL + text).encode()).hexdigest()
            # Only public job vectors are shared. Resume text/embeddings are not.
            hit = cache.execute("SELECT vector FROM vectors WHERE digest=?", (digest,)).fetchone() if owner else None
            if hit:
                vectors[owner] = np.frombuffer(hit[0], np.float32)
                continue
            missing.append((owner, digest))
            for start in range(0, max(1, len(text)), 900):
                chunks.append(text[start:start+1100] or "Resume not supplied")
                owners.append(owner)
        for offset in range(0, len(chunks), 64):
            if progress:
                progress(f"Reading job descriptions · {offset:,} / {len(chunks):,} passages")
            embedded = np.asarray(list(_model.embed(chunks[offset:offset+64], batch_size=16)), np.float32)
            np.add.at(vectors, owners[offset:offset+64], embedded)
        vectors /= np.maximum(np.linalg.norm(vectors, axis=1, keepdims=True), 1e-8)
        with cache:
            for owner, digest in missing:
                if owner:
                    cache.execute("INSERT OR IGNORE INTO vectors VALUES (?,?)", (digest, vectors[owner].tobytes()))
        cache.close()
    # Context enters the senses. It is never used to pick or score a job outside
    # the circuit. A fixed projection keeps similar meanings near each other.
    contextual = np.vstack([vectors[1:] + .25 * vectors[0], vectors[0]])
    return contextual / np.maximum(np.linalg.norm(contextual, axis=1, keepdims=True), 1e-8)


class Sensorium:
    def __init__(self, brain, vectors):
        self.brain = brain
        self.orn = np.flatnonzero(np.char.startswith(brain.cell_type, "ORN_"))
        self.receptor_types, self.receptor_index = np.unique(brain.cell_type[self.orn], return_inverse=True)
        if not len(self.orn):
            raise ValueError("Olfactory receptor annotations are missing.")
        self.visual = brain.visual
        self.chase = [brain.cells(["LC10a"], side=s) for s in "LR"]
        rng = np.random.default_rng(20260912)
        projection = rng.normal(size=(384, len(self.receptor_types))).astype(np.float32)
        raw = np.asarray(vectors) @ projection
        # Analog, sparse receptor responses. No direct Kenyon-cell injection.
        threshold = np.quantile(raw, .65, axis=1, keepdims=True) if len(raw) else raw
        self.odors = np.maximum(raw - threshold, 0)
        self.odors /= np.maximum(self.odors.max(axis=1, keepdims=True), 1e-8) if len(raw) else 1
        self.driven = np.unique(np.concatenate([self.orn, self.visual, *self.chase]))

    def inject_odor(self, index, strength=1.):
        self.brain.v[self.orn, 0] += .6 * strength * self.odors[index, self.receptor_index]

    def vision(self, direction, intensity=1.):
        # The available eye map is one dimensional, not a photorealistic retina.
        # LC10a is an explicit higher-level visual feature channel alongside it.
        direction = float(np.clip(direction, -1, 1))
        eye = np.exp(-((self.brain.azimuth - direction) / .22) ** 2) * intensity
        left, right = max(0., -direction), max(0., direction)
        front = .35 * (1 - abs(direction))
        for ids, drive in zip(self.chase, (left + front, right + front)):
            self.brain.v[ids, 0] += .65 * drive * intensity
        return eye
