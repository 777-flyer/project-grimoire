"""RSA-2048 with OAEP padding, chunked for arbitrary-length plaintext. From
scratch. Handles bulk field encryption; ecc.py handles key wrapping."""

import secrets
from dataclasses import dataclass

from .primes import generate_prime, mod_inverse
from .sha256 import sha256

_HASH_LEN = 32  # SHA-256 output size
_PUBLIC_EXPONENT = 65537


@dataclass(frozen=True)
class RSAPublicKey:
    n: int
    e: int = _PUBLIC_EXPONENT

    @property
    def key_size_bytes(self) -> int:
        return (self.n.bit_length() + 7) // 8


@dataclass(frozen=True)
class RSAPrivateKey:
    n: int
    d: int

    @property
    def key_size_bytes(self) -> int:
        return (self.n.bit_length() + 7) // 8


def generate_keypair(bits: int = 2048) -> tuple:
    half = bits // 2
    while True:
        p = generate_prime(half)
        q = generate_prime(half)
        if p == q:
            continue
        n = p * q
        if n.bit_length() != bits:
            continue
        phi = (p - 1) * (q - 1)
        e = _PUBLIC_EXPONENT
        if phi % e == 0:
            continue
        d = mod_inverse(e, phi)
        return RSAPublicKey(n=n, e=e), RSAPrivateKey(n=n, d=d)


def _mgf1(seed: bytes, mask_len: int) -> bytes:
    output = b""
    counter = 0
    while len(output) < mask_len:
        output += sha256(seed + counter.to_bytes(4, "big"))
        counter += 1
    return output[:mask_len]


def _xor_bytes(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))


class OAEPError(Exception):
    pass


def _oaep_encode(message: bytes, k: int, label: bytes = b"") -> bytes:
    m_len = len(message)
    max_len = k - 2 * _HASH_LEN - 2
    if m_len > max_len:
        raise OAEPError(f"message too long for this key: {m_len} > {max_len} bytes")

    l_hash = sha256(label)
    ps = b"\x00" * (k - m_len - 2 * _HASH_LEN - 2)
    db = l_hash + ps + b"\x01" + message

    seed = secrets.token_bytes(_HASH_LEN)
    db_mask = _mgf1(seed, k - _HASH_LEN - 1)
    masked_db = _xor_bytes(db, db_mask)

    seed_mask = _mgf1(masked_db, _HASH_LEN)
    masked_seed = _xor_bytes(seed, seed_mask)

    return b"\x00" + masked_seed + masked_db


def _oaep_decode(encoded: bytes, k: int, label: bytes = b"") -> bytes:
    if len(encoded) != k or k < 2 * _HASH_LEN + 2:
        raise OAEPError("decryption error")

    y = encoded[0]
    masked_seed = encoded[1:1 + _HASH_LEN]
    masked_db = encoded[1 + _HASH_LEN:]

    seed_mask = _mgf1(masked_db, _HASH_LEN)
    seed = _xor_bytes(masked_seed, seed_mask)
    db_mask = _mgf1(seed, k - _HASH_LEN - 1)
    db = _xor_bytes(masked_db, db_mask)

    l_hash = sha256(label)
    l_hash_prime = db[:_HASH_LEN]
    rest = db[_HASH_LEN:]

    sep_index = rest.find(b"\x01")
    valid = (y == 0) and (l_hash == l_hash_prime) and (sep_index != -1)
    valid = valid and all(b == 0 for b in rest[:max(sep_index, 0)])
    if not valid:
        raise OAEPError("decryption error")

    return rest[sep_index + 1:]


def max_chunk_size(pub: RSAPublicKey) -> int:
    return pub.key_size_bytes - 2 * _HASH_LEN - 2


def encrypt_chunked(plaintext: bytes, pub: RSAPublicKey) -> list:
    """Encrypt arbitrary-length plaintext as an ordered list of fixed-size ciphertext blocks."""
    k = pub.key_size_bytes
    chunk_size = max_chunk_size(pub)
    if chunk_size <= 0:
        raise OAEPError("key too small for OAEP with this hash")

    if plaintext == b"":
        chunks = [b""]
    else:
        chunks = [plaintext[i:i + chunk_size] for i in range(0, len(plaintext), chunk_size)]

    blocks = []
    for chunk in chunks:
        encoded = _oaep_encode(chunk, k)
        m_int = int.from_bytes(encoded, "big")
        c_int = pow(m_int, pub.e, pub.n)
        blocks.append(c_int.to_bytes(k, "big"))
    return blocks


def decrypt_chunked(blocks: list, priv: RSAPrivateKey) -> bytes:
    k = priv.key_size_bytes
    plaintext = b""
    for block in blocks:
        if len(block) != k:
            raise OAEPError("ciphertext block has wrong length")
        c_int = int.from_bytes(block, "big")
        m_int = pow(c_int, priv.d, priv.n)
        encoded = m_int.to_bytes(k, "big")
        plaintext += _oaep_decode(encoded, k)
    return plaintext


def serialize_blocks(blocks: list) -> bytes:
    """Concatenate ciphertext blocks with a 4-byte count prefix, for storage as one BLOB."""
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
