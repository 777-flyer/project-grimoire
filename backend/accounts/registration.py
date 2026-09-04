"""Shared user-creation logic used by both public self-registration
(always DevOps Engineer) and Super Admin provisioning (any role)."""

from django.db import IntegrityError, transaction

from crypto_core.rsa import RSAPublicKey

from . import blind_index, keys, passwords, profile
from .models import User


class RegistrationError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


def create_user(username: str, email: str, contact: str, password: str, role: str) -> tuple:
    """Returns (user, totp_secret). Raises RegistrationError on validation/uniqueness failure."""
    username_lookup = blind_index.compute(username)
    email_lookup = blind_index.compute(email)
    if User.objects.filter(username_lookup=username_lookup).exists():
        raise RegistrationError("username already taken", status=409)
    if User.objects.filter(email_lookup=email_lookup).exists():
        raise RegistrationError("email already registered", status=409)

    key_fields, totp_secret = keys.generate_user_keys()
    password_hash, password_salt = passwords.hash_password(password)

    rsa_pub = RSAPublicKey(n=int(key_fields["rsa_pub_n"]), e=key_fields["rsa_pub_e"])
    profile_fields = profile.encrypt_profile_fields(rsa_pub, username, email, contact)

    try:
        with transaction.atomic():
            user = User.objects.create(
                username_lookup=username_lookup,
                email_lookup=email_lookup,
                password_hash=password_hash,
                password_salt=password_salt,
                role=role,
                **key_fields,
                **profile_fields,
            )
    except IntegrityError:
        raise RegistrationError("username or email already registered", status=409)

    return user, totp_secret
