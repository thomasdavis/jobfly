from types import SimpleNamespace
import pytest
from fastapi import HTTPException
import backend.sessions as sessions


def test_signed_identity_and_separate_state(tmp_path, monkeypatch):
    monkeypatch.setattr(sessions, "STATE", tmp_path)
    factory = lambda path: SimpleNamespace(path=path, clients=1)
    pool = sessions.SessionPool(factory, limit=2)
    a, cookie_a = pool.identity(None)
    b, cookie_b = pool.identity(None)
    assert a != b
    assert pool.identity(cookie_a) == (a, cookie_a)
    assert pool.identity(cookie_b) == (b, cookie_b)
    assert pool.get(a).path != pool.get(b).path
    assert pool.identity(cookie_a[:-1] + ('0' if cookie_a[-1] != '0' else '1'))[0] != a
    with pytest.raises(HTTPException) as caught:
        pool.get(pool.identity(None)[0])
    assert caught.value.status_code == 503


def test_session_survives_server_restart(tmp_path, monkeypatch):
    monkeypatch.setattr(sessions, "STATE", tmp_path)
    pool = sessions.SessionPool(lambda _: None)
    identifier, cookie = pool.identity(None)
    replacement = sessions.SessionPool(lambda _: None)
    assert replacement.identity(cookie)[0] == identifier
