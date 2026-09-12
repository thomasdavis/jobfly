import json
import os
import sqlite3
import hashlib
import zlib
from pathlib import Path

STATE = Path(os.getenv("JOBFLY_STATE", "/mnt/donto-data/donto-resources/research/jobfly-runtime/state"))


class Store:
    def __init__(self, directory=STATE):
        directory.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(directory / "jobfly.sqlite", check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("CREATE TABLE IF NOT EXISTS snapshots (id INTEGER PRIMARY KEY, created TEXT DEFAULT CURRENT_TIMESTAMP, payload TEXT NOT NULL)")
        self.db.execute("CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY, created TEXT DEFAULT CURRENT_TIMESTAMP, job_id TEXT, reward INTEGER, reason TEXT, changed INTEGER)")
        self.db.execute("CREATE TABLE IF NOT EXISTS objects (digest TEXT PRIMARY KEY, payload BLOB NOT NULL)")
        self.db.commit()

    def latest(self):
        row = self.db.execute("SELECT payload FROM snapshots ORDER BY id DESC LIMIT 1").fetchone()
        if not row:
            return None
        payload = json.loads(row[0])
        for path, digest in payload.pop("_storage", {}).items():
            obj = self.db.execute("SELECT payload FROM objects WHERE digest=?", (digest,)).fetchone()
            if not obj:
                raise ValueError("A saved session object is missing.")
            data = json.loads(zlib.decompress(obj[0]))
            if path == "vectors":
                payload["neural"][path] = data
            else:
                payload[path] = data
        return payload

    def save(self, payload, feedback=None):
        # Feedback and resulting checkpoint commit together. Append-only history.
        with self.db:
            # Immutable content-addressed catalog/model arrays avoid duplicating
            # megabytes of unchanged jobs every minute. Old snapshots still load.
            payload = dict(payload)
            payload["neural"] = dict(payload.get("neural", {}))
            references = {}
            for path in ("jobs", "vectors", "factors"):
                parent = payload["neural"] if path == "vectors" else payload
                if path not in parent:
                    continue
                encoded = json.dumps(parent.pop(path), separators=(",", ":")).encode()
                digest = hashlib.sha256(encoded).hexdigest()
                if not self.db.execute("SELECT 1 FROM objects WHERE digest=?", (digest,)).fetchone():
                    self.db.execute("INSERT INTO objects VALUES (?,?)", (digest, zlib.compress(encoded)))
                references[path] = digest
            payload["_storage"] = references
            self.db.execute("INSERT INTO snapshots(payload) VALUES (?)", (json.dumps(payload),))
            if feedback:
                self.db.execute("INSERT INTO feedback(job_id,reward,reason,changed) VALUES (?,?,?,?)", feedback)

    def history(self):
        rows = self.db.execute("SELECT created,job_id,reward,reason,changed FROM feedback ORDER BY id DESC LIMIT 100").fetchall()
        return [dict(zip(("created", "jobId", "reward", "reason", "changed"), r)) for r in rows]
