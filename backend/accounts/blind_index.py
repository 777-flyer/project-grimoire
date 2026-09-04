"""Deterministic HMAC 'blind index' for looking up rows whose real value is
stored only in randomized RSA-OAEP ciphertext (username_enc/email_enc)."""

from django.conf import settings

from crypto_core.hmac import hmac_sha256_hex


def compute(value: str) -> str:
    normalized = value.strip().lower()
    return hmac_sha256_hex(settings.LOOKUP_INDEX_KEY, normalized.encode("utf-8"))
