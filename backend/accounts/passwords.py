"""Password hashing: PBKDF2-HMAC-SHA256 with a per-user random salt, from scratch."""

import secrets

from crypto_core.hmac import constant_time_compare
from crypto_core.pbkdf2 import pbkdf2_hmac_sha256

SALT_SIZE = 16
DKLEN = 32


def hash_password(password: str) -> tuple:
    salt = secrets.token_bytes(SALT_SIZE)
    digest = pbkdf2_hmac_sha256(password.encode("utf-8"), salt, dklen=DKLEN)
    return digest, salt


def verify_password(password: str, stored_hash: bytes, salt: bytes) -> bool:
    candidate = pbkdf2_hmac_sha256(password.encode("utf-8"), salt, dklen=DKLEN)
    return constant_time_compare(candidate, stored_hash)
