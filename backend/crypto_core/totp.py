"""TOTP (RFC 6238) on top of HOTP (RFC 4226), using HMAC-SHA1 for
compatibility with real authenticator apps. Includes a hand-rolled Base32
codec (RFC 4648) for secret provisioning.
"""

import secrets
import time

from .hmac import hmac_sha1, constant_time_compare

_BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
_DEFAULT_DIGITS = 6
_DEFAULT_PERIOD = 30


def base32_encode(data: bytes) -> str:
    bits = "".join(f"{byte:08b}" for byte in data)
    padded_len = -(-len(bits) // 5) * 5
    bits = bits.ljust(padded_len, "0")
    chars = [
        _BASE32_ALPHABET[int(bits[i:i + 5], 2)]
        for i in range(0, len(bits), 5)
    ]
    encoded = "".join(chars)
    pad = (8 - len(encoded) % 8) % 8
    return encoded + "=" * pad


def base32_decode(text: str) -> bytes:
    text = text.rstrip("=").upper()
    bits = "".join(f"{_BASE32_ALPHABET.index(c):05b}" for c in text)
    usable_len = (len(bits) // 8) * 8
    return bytes(int(bits[i:i + 8], 2) for i in range(0, usable_len, 8))


def generate_secret(num_bytes: int = 20) -> bytes:
    return secrets.token_bytes(num_bytes)


def hotp(secret: bytes, counter: int, digits: int = _DEFAULT_DIGITS) -> str:
    counter_bytes = counter.to_bytes(8, "big")
    digest = hmac_sha1(secret, counter_bytes)

    offset = digest[-1] & 0x0F
    truncated = (
        ((digest[offset] & 0x7F) << 24)
        | (digest[offset + 1] << 16)
        | (digest[offset + 2] << 8)
        | digest[offset + 3]
    )
    code = truncated % (10 ** digits)
    return str(code).zfill(digits)


def totp(secret: bytes, timestamp: float = None, digits: int = _DEFAULT_DIGITS,
         period: int = _DEFAULT_PERIOD) -> str:
    if timestamp is None:
        timestamp = time.time()
    counter = int(timestamp // period)
    return hotp(secret, counter, digits)


def verify_totp(secret: bytes, code: str, timestamp: float = None,
                 digits: int = _DEFAULT_DIGITS, period: int = _DEFAULT_PERIOD,
                 window: int = 1) -> bool:
    """Accept the code for the current step or `window` steps before/after,
    to tolerate clock drift between client and server."""
    if timestamp is None:
        timestamp = time.time()
    current_counter = int(timestamp // period)

    for offset in range(-window, window + 1):
        if constant_time_compare(hotp(secret, current_counter + offset, digits).encode(), code.encode()):
            return True
    return False
