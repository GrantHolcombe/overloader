"""Sends sign-in codes through Resend, or prints them in dev when no key is set."""

import logging

import httpx

from app.config import get_settings

log = logging.getLogger("overloader.email")


class EmailError(Exception):
    pass


def send_code(email: str, code: str, minutes: int) -> None:
    settings = get_settings()
    if not settings.resend_api_key:
        if settings.env == "dev":
            # Dev only: the code is a credential, so production never logs it.
            print(f"\n  DEV sign-in code for {email}: {code}\n", flush=True)
            return
        raise EmailError("RESEND_API_KEY is not set")

    res = httpx.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {settings.resend_api_key}",
            "User-Agent": "overloader/0.1",
        },
        json={
            "from": settings.signin_email_from,
            "to": [email],
            "subject": f"{code} is your Overloader sign-in code",
            "text": (
                f"Your Overloader sign-in code is {code}\n\n"
                f"Enter it on the sign-in screen within {minutes} minutes. It works once.\n\n"
                "If you didn't ask to sign in, you can ignore this email; "
                "nobody can get in without the code.\n"
            ),
        },
        timeout=10,
    )
    if res.status_code >= 300:
        raise EmailError(f"Resend {res.status_code} {res.text[:200]}")
