"""Behaviour behind Cloudflare: the client IP header and the origin secret."""

from app.config import get_settings


def request_code(client, email, headers=None):
    return client.post("/api/auth/request-code", json={"email": email}, headers=headers or {})


def test_rate_limit_uses_client_ip_header(client, outbox, monkeypatch):
    monkeypatch.setattr(get_settings(), "client_ip_header", "cf-connecting-ip")
    # 10 codes per IP per hour: the 11th from the same address is refused...
    for i in range(10):
        res = request_code(client, f"u{i}@example.com", {"cf-connecting-ip": "203.0.113.7"})
        assert res.status_code == 200
    assert (
        request_code(client, "u10@example.com", {"cf-connecting-ip": "203.0.113.7"}).status_code
        == 429
    )
    # ...while another user behind the same proxy isn't affected.
    assert (
        request_code(client, "other@example.com", {"cf-connecting-ip": "198.51.100.2"}).status_code
        == 200
    )


def test_origin_secret(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "origin_secret", "s3cret-from-cloudflare")
    assert client.get("/api/me").status_code == 403  # no header: blocked before auth
    assert client.get("/api/me", headers={"x-origin-verify": "wrong"}).status_code == 403
    # Right header: through to the app (which then wants a sign-in).
    assert (
        client.get("/api/me", headers={"x-origin-verify": "s3cret-from-cloudflare"}).status_code
        == 401
    )
    # The readiness check from inside the container needs no header.
    assert client.get("/api/health").status_code == 200


def test_no_origin_secret_means_no_check(client):
    assert get_settings().origin_secret is None
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/me").status_code == 401
