"""Per-user key lifecycle: generate the personal RSA+ECC keypair, wrap the
private halves under the master key for storage, and unwrap them on demand."""

from crypto_core import ecc, rsa
from crypto_core.totp import generate_secret
from grimoire import master_key


def generate_user_keys() -> dict:
    rsa_pub, rsa_priv = rsa.generate_keypair(2048)
    ecc_pub, ecc_priv = ecc.generate_keypair()
    totp_secret = generate_secret()

    return {
        "rsa_pub_n": str(rsa_pub.n),
        "rsa_pub_e": rsa_pub.e,
        "rsa_priv_wrapped": master_key.wrap(rsa_priv.d.to_bytes((rsa_priv.d.bit_length() + 7) // 8 or 1, "big")),
        "ecc_pub_x": str(ecc_pub.point[0]),
        "ecc_pub_y": str(ecc_pub.point[1]),
        "ecc_priv_wrapped": master_key.wrap(ecc_priv.d.to_bytes(32, "big")),
        "totp_secret_wrapped": master_key.wrap(totp_secret),
    }, totp_secret


def get_rsa_public(user) -> rsa.RSAPublicKey:
    return rsa.RSAPublicKey(n=int(user.rsa_pub_n), e=user.rsa_pub_e)


def get_rsa_private(user) -> rsa.RSAPrivateKey:
    d = int.from_bytes(master_key.unwrap(bytes(user.rsa_priv_wrapped)), "big")
    return rsa.RSAPrivateKey(n=int(user.rsa_pub_n), d=d)


def get_ecc_public(user) -> ecc.ECCPublicKey:
    return ecc.ECCPublicKey(point=(int(user.ecc_pub_x), int(user.ecc_pub_y)))


def get_ecc_private(user) -> ecc.ECCPrivateKey:
    d = int.from_bytes(master_key.unwrap(bytes(user.ecc_priv_wrapped)), "big")
    return ecc.ECCPrivateKey(d=d)


def get_totp_secret(user) -> bytes:
    return master_key.unwrap(bytes(user.totp_secret_wrapped))
