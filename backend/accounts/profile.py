"""Encrypt/decrypt a user's profile fields under their own RSA key, with an
HMAC-SHA256 integrity tag over the ciphertext."""

from django.conf import settings

from crypto_core import rsa
from crypto_core.hmac import constant_time_compare, hmac_sha256_hex

from . import keys


class ProfileIntegrityError(Exception):
    pass


def _compute_hmac(username_enc: bytes, email_enc: bytes, contact_enc: bytes) -> str:
    return hmac_sha256_hex(settings.RECORD_HMAC_KEY, username_enc + email_enc + contact_enc)


def encrypt_profile_fields(rsa_pub: rsa.RSAPublicKey, username: str, email: str, contact: str) -> dict:
    username_enc = rsa.serialize_blocks(rsa.encrypt_chunked(username.encode("utf-8"), rsa_pub))
    email_enc = rsa.serialize_blocks(rsa.encrypt_chunked(email.encode("utf-8"), rsa_pub))
    contact_enc = rsa.serialize_blocks(rsa.encrypt_chunked(contact.encode("utf-8"), rsa_pub))
    return {
        "username_enc": username_enc,
        "email_enc": email_enc,
        "contact_enc": contact_enc,
        "profile_hmac": _compute_hmac(username_enc, email_enc, contact_enc),
    }


def decrypt_profile_fields(user) -> dict:
    username_enc = bytes(user.username_enc)
    email_enc = bytes(user.email_enc)
    contact_enc = bytes(user.contact_enc)

    expected = _compute_hmac(username_enc, email_enc, contact_enc)
    if not constant_time_compare(expected.encode(), user.profile_hmac.encode()):
        raise ProfileIntegrityError("profile record failed integrity check, possible tampering")

    rsa_priv = keys.get_rsa_private(user)
    username = rsa.decrypt_chunked(rsa.deserialize_blocks(username_enc), rsa_priv).decode("utf-8")
    email = rsa.decrypt_chunked(rsa.deserialize_blocks(email_enc), rsa_priv).decode("utf-8")
    contact = rsa.decrypt_chunked(rsa.deserialize_blocks(contact_enc), rsa_priv).decode("utf-8")

    return {"username": username, "email": email, "contact": contact}
