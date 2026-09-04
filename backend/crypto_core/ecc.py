"""EC-ElGamal over secp256r1 (NIST P-256), with Koblitz message-to-point
encoding. Implemented from scratch: point arithmetic, keygen, encrypt/decrypt.

Used for key wrapping (see rsa.py for bulk field encryption); avoids
ECDH/ECIES since those require a symmetric cipher downstream.
"""

import secrets
from dataclasses import dataclass

from .primes import extended_gcd

# secp256r1 / NIST P-256 domain parameters
P = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF
A = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFC
B = 0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B
GX = 0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296
GY = 0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5
N = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
G = (GX, GY)

_KOBLITZ_K = 1000       # try up to this many x-offsets; failure prob ~ 2^-1000
_CHUNK_SIZE = 20        # plaintext bytes encoded per curve point (well within the safe margin)
_COORD_SIZE = 32        # bytes per coordinate for a 256-bit curve


class ECCError(Exception):
    pass


def _mod_inverse(a: int, m: int) -> int:
    g, x, _ = extended_gcd(a % m, m)
    if g != 1:
        raise ECCError("modular inverse does not exist")
    return x % m


def is_on_curve(point) -> bool:
    if point is None:
        return True
    x, y = point
    return (y * y - (x * x * x + A * x + B)) % P == 0


def point_add(p1, p2):
    if p1 is None:
        return p2
    if p2 is None:
        return p1

    x1, y1 = p1
    x2, y2 = p2

    if x1 == x2 and (y1 + y2) % P == 0:
        return None  # P + (-P) = infinity

    if p1 == p2:
        if y1 == 0:
            return None
        lam = (3 * x1 * x1 + A) * _mod_inverse(2 * y1, P) % P
    else:
        lam = (y2 - y1) * _mod_inverse((x2 - x1) % P, P) % P

    x3 = (lam * lam - x1 - x2) % P
    y3 = (lam * (x1 - x3) - y1) % P
    return (x3, y3)


def point_negate(point):
    if point is None:
        return None
    x, y = point
    return (x, (-y) % P)


def scalar_mult(k: int, point):
    if point is None or k % N == 0:
        return None
    if k < 0:
        return scalar_mult(-k, point_negate(point))

    result = None
    addend = point
    while k:
        if k & 1:
            result = point_add(result, addend)
        addend = point_add(addend, addend)
        k >>= 1
    return result


@dataclass(frozen=True)
class ECCPublicKey:
    point: tuple


@dataclass(frozen=True)
class ECCPrivateKey:
    d: int


def generate_keypair() -> tuple:
    d = secrets.randbelow(N - 1) + 1
    q = scalar_mult(d, G)
    return ECCPublicKey(point=q), ECCPrivateKey(d=d)


def _tonelli_shanks_sqrt(a: int) -> int:
    """Modular square root mod P. secp256r1's P is 3 mod 4, so this is a direct pow()."""
    if P % 4 != 3:
        raise ECCError("prime does not support the fast sqrt path")
    return pow(a, (P + 1) // 4, P)


def _encode_message_to_point(m_int: int):
    if m_int < 0 or m_int * _KOBLITZ_K + (_KOBLITZ_K - 1) >= P:
        raise ECCError("message integer out of range for Koblitz encoding")

    for j in range(_KOBLITZ_K):
        x = m_int * _KOBLITZ_K + j
        rhs = (x * x * x + A * x + B) % P
        y = _tonelli_shanks_sqrt(rhs)
        if (y * y) % P == rhs:
            return (x, y)
    raise ECCError("failed to encode message as a curve point (statistically near-impossible)")


def _decode_point_to_message(point) -> int:
    x, _ = point
    return x // _KOBLITZ_K


def elgamal_encrypt_point(message_point, recipient_pub: ECCPublicKey):
    k = secrets.randbelow(N - 1) + 1
    c1 = scalar_mult(k, G)
    c2 = point_add(message_point, scalar_mult(k, recipient_pub.point))
    return c1, c2


def elgamal_decrypt_point(c1, c2, priv: ECCPrivateKey):
    shared = scalar_mult(priv.d, c1)
    return point_add(c2, point_negate(shared))


def _point_to_bytes(point) -> bytes:
    if point is None:
        return b"\x00" * (2 * _COORD_SIZE)
    x, y = point
    return x.to_bytes(_COORD_SIZE, "big") + y.to_bytes(_COORD_SIZE, "big")


def _bytes_to_point(data: bytes):
    x = int.from_bytes(data[:_COORD_SIZE], "big")
    y = int.from_bytes(data[_COORD_SIZE:], "big")
    if x == 0 and y == 0:
        return None
    return (x, y)


def encrypt_chunked(data: bytes, recipient_pub: ECCPublicKey) -> list:
    """Encrypt arbitrary-length bytes as an ordered list of EC-ElGamal ciphertext blocks."""
    header = len(data).to_bytes(4, "big")
    payload = header + data
    pad_len = (-len(payload)) % _CHUNK_SIZE
    payload += b"\x00" * pad_len

    blocks = []
    for i in range(0, len(payload), _CHUNK_SIZE):
        chunk = payload[i:i + _CHUNK_SIZE]
        m_int = int.from_bytes(chunk, "big")
        point = _encode_message_to_point(m_int)
        c1, c2 = elgamal_encrypt_point(point, recipient_pub)
        blocks.append(_point_to_bytes(c1) + _point_to_bytes(c2))
    return blocks


def decrypt_chunked(blocks: list, priv: ECCPrivateKey) -> bytes:
    payload = b""
    block_size = 4 * _COORD_SIZE
    for block in blocks:
        if len(block) != block_size:
            raise ECCError("ciphertext block has wrong length")
        c1 = _bytes_to_point(block[:2 * _COORD_SIZE])
        c2 = _bytes_to_point(block[2 * _COORD_SIZE:])
        point = elgamal_decrypt_point(c1, c2, priv)
        m_int = _decode_point_to_message(point)
        payload += m_int.to_bytes(_CHUNK_SIZE, "big")

    length = int.from_bytes(payload[:4], "big")
    return payload[4:4 + length]


def serialize_blocks(blocks: list) -> bytes:
    out = len(blocks).to_bytes(4, "big")
    for block in blocks:
        out += len(block).to_bytes(4, "big") + block
    return out


def deserialize_blocks(data: bytes) -> list:
    count = int.from_bytes(data[:4], "big")
    offset = 4
    blocks = []
    for _ in range(count):
        length = int.from_bytes(data[offset:offset + 4], "big")
        offset += 4
        blocks.append(data[offset:offset + length])
        offset += length
    return blocks
