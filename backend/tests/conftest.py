"""Tests run against a real Postgres named by TEST_DATABASE_URL (CI uses a service container).

The database is migrated to head once, and user data is wiped between tests. Never point this
at a database you care about.
"""

import os

import pytest
from dotenv import dotenv_values

ENV_FILE = os.path.join(os.path.dirname(__file__), "..", ".env")
TEST_URL = os.environ.get("TEST_DATABASE_URL") or dotenv_values(ENV_FILE).get("TEST_DATABASE_URL")
if not TEST_URL:
    pytest.exit("TEST_DATABASE_URL is not set (see backend/.env.example)", returncode=1)

os.environ["DATABASE_URL"] = TEST_URL
os.environ["ENV"] = "test"
os.environ["JWT_SECRET"] = "test-secret-that-is-long-enough-for-hs256"
os.environ.pop("RESEND_API_KEY", None)

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.catalog import read_catalog, sync  # noqa: E402
from app.db import get_engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def migrated():
    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option(
        "script_location", os.path.join(os.path.dirname(__file__), "..", "migrations")
    )
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    reset_catalog()


def reset_catalog():
    """Puts the catalog back to exactly catalog/exercises.csv (tests may add or retire rows)."""
    names = [n.lower() for n, _, _ in read_catalog()[0]]
    with get_engine().begin() as conn:
        conn.execute(
            text("DELETE FROM exercise WHERE user_id IS NULL AND NOT (lower(name) = ANY(:names))"),
            {"names": names},
        )
    with Session(get_engine()) as db:
        sync(db, write=True)


@pytest.fixture(autouse=True)
def clean_db():
    yield
    with get_engine().begin() as conn:
        # Not TRUNCATE ... CASCADE: exercise references app_user, so that would empty the
        # whole catalog too.
        conn.execute(text("DELETE FROM log_entry"))
        conn.execute(text("DELETE FROM exercise WHERE user_id IS NOT NULL"))
        conn.execute(text("DELETE FROM email_login_code"))
        conn.execute(text("DELETE FROM app_user"))
    reset_catalog()


@pytest.fixture
def outbox(monkeypatch):
    """Captures sign-in codes instead of emailing them."""
    sent: dict[str, str] = {}
    monkeypatch.setattr(
        "app.routers.auth.send_code", lambda email, code, minutes: sent.__setitem__(email, code)
    )
    return sent


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def signed_in(client, outbox):
    """Returns a function that signs an address in and gives back auth headers."""

    def sign_in(email="lifter@example.com"):
        assert client.post("/api/auth/request-code", json={"email": email}).status_code == 200
        # Codes are sent to the normalized address.
        code = outbox[email.strip().lower()]
        res = client.post("/api/auth/verify", json={"email": email, "code": code})
        assert res.status_code == 200, res.text
        return {"Authorization": f"Bearer {res.json()['token']}"}

    return sign_in
