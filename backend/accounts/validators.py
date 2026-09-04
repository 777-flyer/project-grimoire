"""Password strength rules, hand-rolled since django.contrib.auth's
validators aren't available (that app isn't installed; see settings.py)."""

import re


class WeakPasswordError(ValueError):
    pass


MIN_LENGTH = 10


def validate_password_strength(password: str, username: str = "", email: str = "") -> None:
    if len(password) < MIN_LENGTH:
        raise WeakPasswordError(f"Password must be at least {MIN_LENGTH} characters long.")
    if not re.search(r"[a-z]", password):
        raise WeakPasswordError("Password must contain a lowercase letter.")
    if not re.search(r"[A-Z]", password):
        raise WeakPasswordError("Password must contain an uppercase letter.")
    if not re.search(r"[0-9]", password):
        raise WeakPasswordError("Password must contain a digit.")
    if not re.search(r"[^a-zA-Z0-9]", password):
        raise WeakPasswordError("Password must contain a symbol.")
    if username and username.lower() in password.lower():
        raise WeakPasswordError("Password must not contain the username.")
    if email and email.split("@")[0].lower() in password.lower():
        raise WeakPasswordError("Password must not contain the email address.")
