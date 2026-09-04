"""Wrap/unwrap private-key material under the master RSA keypair (settings.py).

The master private key lives only in the environment, never in the
database or source control.
"""

from django.conf import settings

from crypto_core import rsa


def get_master_public_key() -> rsa.RSAPublicKey:
    if settings.MASTER_PUBLIC_KEY_N is None:
        raise RuntimeError("MASTER_PUBLIC_KEY_N is not configured, run scripts/generate_master_key.py")
    return rsa.RSAPublicKey(n=settings.MASTER_PUBLIC_KEY_N, e=settings.MASTER_PUBLIC_KEY_E)


def get_master_private_key() -> rsa.RSAPrivateKey:
    if settings.MASTER_PRIVATE_KEY_D is None:
        raise RuntimeError("MASTER_PRIVATE_KEY_D is not configured, run scripts/generate_master_key.py")
    return rsa.RSAPrivateKey(n=settings.MASTER_PUBLIC_KEY_N, d=settings.MASTER_PRIVATE_KEY_D)


def wrap(data: bytes) -> bytes:
    """RSA-OAEP chunk-encrypt data to the master public key, for storage."""
    blocks = rsa.encrypt_chunked(data, get_master_public_key())
    return rsa.serialize_blocks(blocks)


def unwrap(blob: bytes) -> bytes:
    """Decrypt data previously produced by wrap(), using the master private key."""
    blocks = rsa.deserialize_blocks(blob)
    return rsa.decrypt_chunked(blocks, get_master_private_key())
