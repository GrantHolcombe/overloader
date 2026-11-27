import logging

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app import auth
from app.auth import DB, CurrentUser
from app.email import EmailError, send_code
from app.models import User
from app.schemas import CodeRequest, CodeVerify, TokenOut, UserOut, UserUpdate

router = APIRouter(prefix="/api", tags=["auth"])
log = logging.getLogger("overloader.auth")


@router.post("/auth/request-code")
def request_code(body: CodeRequest, request: Request, db: DB) -> dict:
    """Emails a sign-in code. Same answer whether or not the address has an account."""
    email = auth.normalize(body.email)
    ip = auth.client_ip(request)
    if auth.rate_limited(db, email, ip):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many codes requested. Wait a few minutes and try again.",
        )
    code = auth.create_code(db, email, ip)
    try:
        send_code(email, code, auth.CODE_MINUTES)
    except EmailError as err:
        log.error("sign-in code email failed: %s", err)
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "We couldn't send the email. Try again in a minute."
        ) from None
    return {"sent": True}


@router.post("/auth/verify")
def verify(body: CodeVerify, db: DB) -> TokenOut:
    """Checks the code; the email address is the identity, so first sign-in creates the user."""
    email = auth.normalize(body.email)
    if not auth.check_code(db, email, body.code):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "That code didn't work. Check it or send a new one."
        )
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email)
        db.add(user)
        db.commit()
        db.refresh(user)
    return TokenOut(token=auth.issue_token(user), user=UserOut.model_validate(user))


@router.get("/me")
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.patch("/me")
def update_me(body: UserUpdate, user: CurrentUser, db: DB) -> UserOut:
    user.unit = body.unit
    db.commit()
    return UserOut.model_validate(user)
