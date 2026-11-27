"""Email sign-in with a 6-digit one-time code, then a signed JWT. No passwords.

Codes are stored as an HMAC (never the code itself), last 10 minutes, work once, allow 5
guesses, and a new code expires the older ones. Sending is rate limited per address and per IP.
"""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import EmailLoginCode, User

CODE_MINUTES = 10
MAX_GUESSES = 5
LIMIT_EMAIL_15_MIN = 3
LIMIT_EMAIL_DAY = 10
LIMIT_IP_HOUR = 10


def normalize(email: str) -> str:
    return email.strip().lower()


def client_ip(request: Request) -> str | None:
    """The user's address for rate limiting: the configured header (Cloudflare's
    cf-connecting-ip in production) when present, otherwise the connection's address."""
    header = get_settings().client_ip_header
    if header:
        value = request.headers.get(header, "").strip()
        if value:
            return value[:45]  # longest IPv6 text form; the column is 45 characters
    return request.client.host if request.client else None


def _hash(email: str, code: str) -> str:
    key = get_settings().jwt_secret.encode()
    return hmac.new(key, f"{email}:{code}".encode(), hashlib.sha256).hexdigest()


def rate_limited(db: Session, email: str, ip: str | None) -> bool:
    now = datetime.now(UTC)
    c = EmailLoginCode
    email_15m, email_day, ip_hour = db.execute(
        select(
            func.count().filter(c.email == email, c.created_at > now - timedelta(minutes=15)),
            func.count().filter(c.email == email),
            func.count().filter(c.request_ip == ip, c.created_at > now - timedelta(hours=1)),
        ).where(c.created_at > now - timedelta(days=1), or_(c.email == email, c.request_ip == ip))
    ).one()
    return (
        email_15m >= LIMIT_EMAIL_15_MIN
        or email_day >= LIMIT_EMAIL_DAY
        or (ip is not None and ip_hour >= LIMIT_IP_HOUR)
    )


def create_code(db: Session, email: str, ip: str | None) -> str:
    now = datetime.now(UTC)
    code = f"{secrets.randbelow(1_000_000):06d}"
    c = EmailLoginCode
    db.execute(delete(c).where(c.created_at < now - timedelta(days=1)))
    db.execute(
        update(c)
        .where(c.email == email, c.consumed_at.is_(None), c.expires_at > now)
        .values(expires_at=now)
    )
    db.add(
        c(
            email=email,
            code_hash=_hash(email, code),
            request_ip=ip,
            expires_at=now + timedelta(minutes=CODE_MINUTES),
        )
    )
    db.commit()
    return code


def check_code(db: Session, email: str, code: str) -> bool:
    """Counts the guess first (atomically), then compares in constant time."""
    code = "".join(code.split())
    if not (len(code) == 6 and code.isdigit()):
        return False
    now = datetime.now(UTC)
    c = EmailLoginCode
    latest = (
        select(c.id)
        .where(c.email == email, c.consumed_at.is_(None), c.expires_at > now)
        .order_by(c.created_at.desc(), c.id.desc())
        .limit(1)
        .scalar_subquery()
    )
    row = db.execute(
        update(c)
        .where(c.id == latest, c.attempts < MAX_GUESSES)
        .values(attempts=c.attempts + 1)
        .returning(c.id, c.code_hash)
    ).one_or_none()
    db.commit()
    if row is None or not hmac.compare_digest(row.code_hash, _hash(email, code)):
        return False
    # Use it up; a second request with the same code gets nothing.
    used = db.execute(
        update(c)
        .where(c.id == row.id, c.consumed_at.is_(None))
        .values(consumed_at=now)
        .returning(c.id)
    ).one_or_none()
    db.commit()
    return used is not None


def issue_token(user: User) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {"sub": str(user.id), "iat": now, "exp": now + timedelta(days=settings.token_days)}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


bearer = HTTPBearer(auto_error=False)
DB = Annotated[Session, Depends(get_db)]


def current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)], db: DB
) -> User:
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in again")
    if creds is None:
        raise unauthorized
    try:
        payload = jwt.decode(creds.credentials, get_settings().jwt_secret, algorithms=["HS256"])
        user = db.get(User, int(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise unauthorized from None
    if user is None:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(current_user)]
