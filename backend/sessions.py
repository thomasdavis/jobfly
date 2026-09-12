"""Opaque signed browser identities and a bounded pool of isolated brains."""
import hashlib
import hmac
import os
import secrets
import threading
import time

from fastapi import HTTPException

from .storage import STATE


class SessionPool:
    def __init__(self, factory, limit=2):
        self.factory, self.limit = factory, limit
        self.lock = threading.Lock()
        self.engines = {}
        STATE.mkdir(parents=True, exist_ok=True)
        key_path = STATE / "session.key"
        if not key_path.exists():
            fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(secrets.token_bytes(32))
        self.key = key_path.read_bytes()

    def identity(self, cookie):
        if cookie:
            parts = cookie.split(".")
            if len(parts) == 2 and len(parts[0]) == 48:
                identifier, signature = parts
                expected = hmac.new(self.key, identifier.encode(), hashlib.sha256).hexdigest()
                if all(c in "0123456789abcdef" for c in identifier) and hmac.compare_digest(signature, expected):
                    return identifier, cookie
        identifier = secrets.token_hex(24)
        signature = hmac.new(self.key, identifier.encode(), hashlib.sha256).hexdigest()
        return identifier, f"{identifier}.{signature}"

    def get(self, identifier):
        with self.lock:
            now = time.monotonic()
            # Retire disconnected sessions. Learning already lives in SQLite.
            for key, (engine, touched) in list(self.engines.items()):
                if key != identifier and engine.clients == 0 and now - touched > 45:
                    engine.stopped = True
                    engine.thread.join(timeout=1)
                    if not engine.thread.is_alive():
                        engine.store.db.close()
                        del self.engines[key]
            if identifier not in self.engines:
                if len(self.engines) >= self.limit:
                    raise HTTPException(503, "The habitat is busy. Its resident brains are already exploring; please try again shortly.")
                self.engines[identifier] = (self.factory(STATE / identifier), now)
            engine, _ = self.engines[identifier]
            self.engines[identifier] = (engine, now)
            return engine

    def close(self):
        for engine, _ in self.engines.values():
            engine.stopped = True
        for engine, _ in self.engines.values():
            engine.thread.join(timeout=4)
            if not engine.thread.is_alive():
                engine.store.db.close()
