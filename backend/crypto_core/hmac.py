"""HMAC (RFC 2104), built on our from-scratch SHA-256 and SHA-1."""

from .sha1 import sha1
from .sha256 import sha256

_BLOCK_SIZE = 64  # both SHA-256 and SHA-1 use a 64-byte block


def _hmac(hash_fn, key: bytes, message: bytes) -> bytes:
    if len(key) > _BLOCK_SIZE:
        key = hash_fn(key)
    key = key + b"\x00" * (_BLOCK_SIZE - len(key))

    o_key_pad = bytes(b ^ 0x5C for b in key)
    i_key_pad = bytes(b ^ 0x36 for b in key)

    return hash_fn(o_key_pad + hash_fn(i_key_pad + message))


def hmac_sha256(key: bytes, message: bytes) -> bytes:
    return _hmac(sha256, key, message)


def hmac_sha256_hex(key: bytes, message: bytes) -> str:
    return hmac_sha256(key, message).hex()


def hmac_sha1(key: bytes, message: bytes) -> bytes:
    """Used only by totp.py, for compatibility with authenticator apps."""
    return _hmac(sha1, key, message)


def constant_time_compare(a: bytes, b: bytes) -> bool:
    """Compare two byte strings without leaking timing info via early exit."""
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b):
        result |= x ^ y
    return result == 0
