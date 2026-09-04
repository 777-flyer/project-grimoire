"""Login rate limiting: repeated failed attempts lock the account out for a
cooldown window instead of allowing unlimited password guesses."""

from datetime import timedelta

from django.utils import timezone

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60


def is_locked(user) -> bool:
    return user.locked_until is not None and user.locked_until > timezone.now()


def lockout_remaining_seconds(user) -> int:
    if user.locked_until is None:
        return 0
    return max(0, int((user.locked_until - timezone.now()).total_seconds()))


def register_failed_attempt(user) -> None:
    user.failed_login_attempts += 1
    if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
        user.locked_until = timezone.now() + timedelta(seconds=LOCKOUT_SECONDS)
        user.failed_login_attempts = 0
    user.save(update_fields=["failed_login_attempts", "locked_until"])


def register_successful_attempt(user) -> None:
    if user.failed_login_attempts or user.locked_until:
        user.failed_login_attempts = 0
        user.locked_until = None
        user.save(update_fields=["failed_login_attempts", "locked_until"])
