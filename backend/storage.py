import json
import os
import sqlite3
from pathlib import Path

STATE = Path(os.getenv("JOBFLY_STATE", "/mnt/donto-data/donto-resources/research/jobfly-runtime/state"))


class Store:
    def __init__(self, directory=STATE):
        directory.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(directory / "jobfly.sqlite", check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("CREATE TABLE IF NOT EXISTS snapshots (id INTEGER PRIMARY KEY, created TEXT DEFAULT CURRENT_TIMESTAMP, payload TEXT NOT NULL)")
        self.db.execute("CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY, created TEXT DEFAULT CURRENT_TIMESTAMP, job_id TEXT, reward INTEGER, reason TEXT, changed INTEGER)")
        self.db.commit()

    def latest(self):
        row = self.db.execute("SELECT payload FROM snapshots ORDER BY id DESC LIMIT 1").fetchone()
        return json.loads(row[0]) if row else None

    def save(self, payload, feedback=None):
        # Feedback and resulting checkpoint commit together. Append-only history.
        with self.db:
            self.db.execute("INSERT INTO snapshots(payload) VALUES (?)", (json.dumps(payload),))
            if feedback:
                self.db.execute("INSERT INTO feedback(job_id,reward,reason,changed) VALUES (?,?,?,?)", feedback)

    def history(self):
        rows = self.db.execute("SELECT created,job_id,reward,reason,changed FROM feedback ORDER BY id DESC LIMIT 100").fetchall()
        return [dict(zip(("created", "jobId", "reward", "reason", "changed"), r)) for r in rows]
