from sqlalchemy import select

from app.db import get_engine
from app.models import EmailLoginCode


def test_sign_in_creates_user_once(client, outbox, signed_in):
    headers = signed_in("Lifter@Example.com ")
    me = client.get("/api/me", headers=headers).json()
    assert me["email"] == "lifter@example.com"
    assert me["unit"] == "lb"

    again = signed_in("lifter@example.com")
    assert client.get("/api/me", headers=again).json()["id"] == me["id"]


def test_code_is_stored_hashed(client, outbox):
    client.post("/api/auth/request-code", json={"email": "a@example.com"})
    with get_engine().connect() as conn:
        stored = conn.execute(select(EmailLoginCode.code_hash)).scalar_one()
    assert outbox["a@example.com"] not in stored


def test_code_works_once(client, outbox):
    client.post("/api/auth/request-code", json={"email": "a@example.com"})
    body = {"email": "a@example.com", "code": outbox["a@example.com"]}
    assert client.post("/api/auth/verify", json=body).status_code == 200
    assert client.post("/api/auth/verify", json=body).status_code == 401


def test_wrong_code_and_guess_limit(client, outbox):
    client.post("/api/auth/request-code", json={"email": "a@example.com"})
    real = outbox["a@example.com"]
    wrong = "000000" if real != "000000" else "111111"
    for _ in range(5):
        res = client.post("/api/auth/verify", json={"email": "a@example.com", "code": wrong})
        assert res.status_code == 401
    # Out of guesses: even the right code fails now.
    res = client.post("/api/auth/verify", json={"email": "a@example.com", "code": real})
    assert res.status_code == 401


def test_new_code_expires_old_one(client, outbox):
    client.post("/api/auth/request-code", json={"email": "a@example.com"})
    first = outbox["a@example.com"]
    client.post("/api/auth/request-code", json={"email": "a@example.com"})
    if outbox["a@example.com"] != first:
        res = client.post("/api/auth/verify", json={"email": "a@example.com", "code": first})
        assert res.status_code == 401


def test_rate_limit_per_email(client, outbox):
    for _ in range(3):
        assert (
            client.post("/api/auth/request-code", json={"email": "a@example.com"}).status_code
            == 200
        )
    assert client.post("/api/auth/request-code", json={"email": "a@example.com"}).status_code == 429


def test_bad_email_rejected(client):
    assert client.post("/api/auth/request-code", json={"email": "nope"}).status_code == 422


def test_requires_token(client):
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/me", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_change_unit(client, signed_in):
    headers = signed_in()
    assert client.patch("/api/me", json={"unit": "kg"}, headers=headers).json()["unit"] == "kg"
    assert client.patch("/api/me", json={"unit": "stone"}, headers=headers).status_code == 422
