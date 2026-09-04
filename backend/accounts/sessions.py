"""Session tokens: a random opaque token is handed to the client; only its
HMAC is stored server-side. Sessions are bound to a device fingerprint.
"""

import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from crypto_core.hmac import constant_time_compare, hmac_sha256_hex

from .models import PendingLogin, Session

TOKEN_BYTES = 32
PENDING_LOGIN_LIFETIME_SECONDS = 300  # 5 minutes to complete 2FA


def _sign(raw_token: str) -> str:
    return hmac_sha256_hex(settings.SESSION_SIGNING_KEY, raw_token.encode("utf-8"))


def create_pending_login(user, device_fingerprint: str) -> str:
    raw_ticket = secrets.token_urlsafe(TOKEN_BYTES)
    PendingLogin.objects.create(
        user=user,
        ticket_hmac=_sign(raw_ticket),
        device_fingerprint=device_fingerprint,
        expires_at=timezone.now() + timedelta(seconds=PENDING_LOGIN_LIFETIME_SECONDS),
    )
    return raw_ticket


def resolve_pending_login(raw_ticket: str, device_fingerprint: str):
    """Return the PendingLogin if valid and unused, else None. Does not
    consume it; call consume_pending_login only after TOTP verifies."""
    ticket_hmac = _sign(raw_ticket)
    try:
        pending = PendingLogin.objects.select_related("user").get(ticket_hmac=ticket_hmac)
    except PendingLogin.DoesNotExist:
        return None

    if pending.consumed_at is not None:
        return None
    if pending.expires_at < timezone.now():
        return None
    if not constant_time_compare(pending.device_fingerprint.encode(), device_fingerprint.encode()):
        return None

    return pending


def consume_pending_login(pending: PendingLogin) -> None:
    pending.consumed_at = timezone.now()
    pending.save(update_fields=["consumed_at"])


def create_session(user, device_fingerprint: str) -> str:
    raw_token = secrets.token_urlsafe(TOKEN_BYTES)
    Session.objects.create(
        user=user,
        token_hmac=_sign(raw_token),
        device_fingerprint=device_fingerprint,
        expires_at=timezone.now() + timedelta(seconds=settings.SESSION_TOKEN_LIFETIME_SECONDS),
    )
    return raw_token


def resolve_session(raw_token: str, device_fingerprint: str):
    """Return the active Session for this token, or None if missing, expired,
    revoked, or device-mismatched."""
    if not raw_token:
        return None
    token_hmac = _sign(raw_token)
    try:
        session = Session.objects.select_related("user").get(token_hmac=token_hmac)
    except Session.DoesNotExist:
        return None

    if session.revoked_at is not None:
        return None
    if session.expires_at < timezone.now():
        return None
    if not constant_time_compare(session.device_fingerprint.encode(), device_fingerprint.encode()):
        return None
    return session


def rotate_session(session) -> str:
    """Issue a fresh token for the same user/device and revoke the old one."""
    session.revoked_at = timezone.now()
    session.save(update_fields=["revoked_at"])
    return create_session(session.user, session.device_fingerprint)


def revoke_session(session) -> None:
    session.revoked_at = timezone.now()
    session.save(update_fields=["revoked_at"])
