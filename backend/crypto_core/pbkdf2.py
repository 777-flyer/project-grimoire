"""PBKDF2-HMAC-SHA256 (RFC 8018), built on our from-scratch HMAC."""

from .hmac import hmac_sha256

_DIGEST_SIZE = 32

# Lower than OWASP's 210,000 recommendation because this is pure-Python
# SHA-256 rather than hardware-accelerated; keeps logins responsive.
DEFAULT_ITERATIONS = 1_000


def pbkdf2_hmac_sha256(password: bytes, salt: bytes, iterations: int = DEFAULT_ITERATIONS, dklen: int = 32) -> bytes:
    if dklen <= 0:
        raise ValueError("dklen must be positive")

    num_blocks = -(-dklen // _DIGEST_SIZE)  # ceil division
    output = b""

    for block_index in range(1, num_blocks + 1):
        u = hmac_sha256(password, salt + block_index.to_bytes(4, "big"))
        t = bytearray(u)
        for _ in range(iterations - 1):
            u = hmac_sha256(password, u)
            for i in range(_DIGEST_SIZE):
                t[i] ^= u[i]
        output += bytes(t)

    return output[:dklen]
