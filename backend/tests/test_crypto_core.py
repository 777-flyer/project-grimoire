"""Correctness tests for crypto_core, checked against known reference vectors
where available and against Python's stdlib (hashlib/hmac) purely as an
external oracle for fuzz-testing our from-scratch implementations. The
stdlib is never used by the application itself.
"""

import hashlib
import hmac as std_hmac
import os
import time
import unittest

from crypto_core import ecc, rsa
from crypto_core.hmac import constant_time_compare, hmac_sha1, hmac_sha256
from crypto_core.pbkdf2 import pbkdf2_hmac_sha256
from crypto_core.primes import generate_prime, is_probable_prime, mod_inverse
from crypto_core.sha1 import sha1
from crypto_core.sha256 import sha256
from crypto_core.totp import (base32_decode, base32_encode, generate_secret,
                               hotp, totp, verify_totp)


class Sha256Tests(unittest.TestCase):
    def test_known_vectors(self):
        self.assertEqual(sha256(b"").hex(),
                          "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
        self.assertEqual(sha256(b"abc").hex(),
                          "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")

    def test_matches_hashlib_across_lengths(self):
        for length in (0, 1, 55, 56, 57, 63, 64, 65, 1000):
            msg = os.urandom(length)
            self.assertEqual(sha256(msg), hashlib.sha256(msg).digest())


class Sha1Tests(unittest.TestCase):
    def test_known_vectors(self):
        self.assertEqual(sha1(b"").hex(), "da39a3ee5e6b4b0d3255bfef95601890afd80709")
        self.assertEqual(sha1(b"abc").hex(), "a9993e364706816aba3e25717850c26c9cd0d89d")

    def test_matches_hashlib_across_lengths(self):
        for length in (0, 1, 55, 56, 57, 63, 64, 65, 1000):
            msg = os.urandom(length)
            self.assertEqual(sha1(msg), hashlib.sha1(msg).digest())


class HmacTests(unittest.TestCase):
    def test_rfc4231_case1(self):
        key = bytes.fromhex("0b" * 20)
        msg = b"Hi There"
        expected = bytes.fromhex(
            "b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7"[:64]
        )
        self.assertEqual(hmac_sha256(key, msg), expected)

    def test_matches_stdlib_hmac(self):
        for key_len, msg_len in ((20, 0), (80, 50), (32, 1000)):
            key, msg = os.urandom(key_len), os.urandom(msg_len)
            self.assertEqual(hmac_sha256(key, msg),
                              std_hmac.new(key, msg, hashlib.sha256).digest())

    def test_hmac_sha1_matches_stdlib(self):
        for key_len, msg_len in ((20, 0), (80, 50), (32, 1000)):
            key, msg = os.urandom(key_len), os.urandom(msg_len)
            self.assertEqual(hmac_sha1(key, msg),
                              std_hmac.new(key, msg, hashlib.sha1).digest())

    def test_constant_time_compare(self):
        self.assertTrue(constant_time_compare(b"abc", b"abc"))
        self.assertFalse(constant_time_compare(b"abc", b"abd"))
        self.assertFalse(constant_time_compare(b"abc", b"ab"))


class Pbkdf2Tests(unittest.TestCase):
    def test_matches_hashlib(self):
        got = pbkdf2_hmac_sha256(b"password", b"salt", iterations=4096, dklen=32)
        expected = hashlib.pbkdf2_hmac("sha256", b"password", b"salt", 4096, dklen=32)
        self.assertEqual(got, expected)

    def test_dklen_not_multiple_of_digest(self):
        got = pbkdf2_hmac_sha256(b"pw", b"salt", iterations=1000, dklen=40)
        expected = hashlib.pbkdf2_hmac("sha256", b"pw", b"salt", 1000, dklen=40)
        self.assertEqual(got, expected)


class PrimesTests(unittest.TestCase):
    def test_known_primality(self):
        self.assertTrue(is_probable_prime(97))
        self.assertFalse(is_probable_prime(561))  # Carmichael number
        self.assertFalse(is_probable_prime(1))

    def test_mod_inverse(self):
        self.assertEqual((3 * mod_inverse(3, 11)) % 11, 1)

    def test_generate_prime_has_requested_bit_length(self):
        p = generate_prime(256)
        self.assertEqual(p.bit_length(), 256)
        self.assertTrue(is_probable_prime(p))


class RsaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pub, cls.priv = rsa.generate_keypair(2048)

    def test_keysize(self):
        self.assertEqual(self.pub.n.bit_length(), 2048)

    def test_roundtrip_single_block(self):
        msg = b"Hello, Grimoire!"
        blocks = rsa.encrypt_chunked(msg, self.pub)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(rsa.decrypt_chunked(blocks, self.priv), msg)

    def test_roundtrip_empty(self):
        blocks = rsa.encrypt_chunked(b"", self.pub)
        self.assertEqual(rsa.decrypt_chunked(blocks, self.priv), b"")

    def test_roundtrip_multi_block(self):
        msg = b"A" * 1000 + b"B" * 500
        blocks = rsa.encrypt_chunked(msg, self.pub)
        self.assertGreater(len(blocks), 1)
        self.assertEqual(rsa.decrypt_chunked(blocks, self.priv), msg)

    def test_exact_chunk_boundary(self):
        size = rsa.max_chunk_size(self.pub)
        msg = b"X" * size
        blocks = rsa.encrypt_chunked(msg, self.pub)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(rsa.decrypt_chunked(blocks, self.priv), msg)

    def test_serialize_roundtrip(self):
        blocks = rsa.encrypt_chunked(b"serialize me", self.pub)
        data = rsa.serialize_blocks(blocks)
        self.assertEqual(rsa.deserialize_blocks(data), blocks)

    def test_tamper_detected(self):
        blocks = rsa.encrypt_chunked(b"secret", self.pub)
        tampered = bytearray(blocks[0])
        tampered[-1] ^= 0xFF
        with self.assertRaises(rsa.OAEPError):
            rsa.decrypt_chunked([bytes(tampered)], self.priv)


class EccTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pub, cls.priv = ecc.generate_keypair()

    def test_generator_on_curve_and_correct_order(self):
        self.assertTrue(ecc.is_on_curve(ecc.G))
        self.assertIsNone(ecc.scalar_mult(ecc.N, ecc.G))

    def test_public_key_on_curve(self):
        self.assertTrue(ecc.is_on_curve(self.pub.point))

    def test_koblitz_encode_decode(self):
        for value in (0, 1, 255, 123456789, 1 << 150):
            point = ecc._encode_message_to_point(value)
            self.assertTrue(ecc.is_on_curve(point))
            self.assertEqual(ecc._decode_point_to_message(point), value)

    def test_elgamal_point_roundtrip(self):
        point = ecc.scalar_mult(12345, ecc.G)
        c1, c2 = ecc.elgamal_encrypt_point(point, self.pub)
        self.assertEqual(ecc.elgamal_decrypt_point(c1, c2, self.priv), point)

    def test_chunked_roundtrip(self):
        msg = b"access-grant-token-xyz"
        blocks = ecc.encrypt_chunked(msg, self.pub)
        self.assertEqual(ecc.decrypt_chunked(blocks, self.priv), msg)

    def test_chunked_roundtrip_empty(self):
        blocks = ecc.encrypt_chunked(b"", self.pub)
        self.assertEqual(ecc.decrypt_chunked(blocks, self.priv), b"")

    def test_wraps_rsa_private_key(self):
        """The real use case: an EC-ElGamal-wrapped project RSA private key."""
        _, rsa_priv = rsa.generate_keypair(2048)
        payload = rsa_priv.n.to_bytes(256, "big") + rsa_priv.d.to_bytes(256, "big")
        wrapped = ecc.encrypt_chunked(payload, self.pub)
        self.assertEqual(ecc.decrypt_chunked(wrapped, self.priv), payload)

    def test_serialize_roundtrip(self):
        blocks = ecc.encrypt_chunked(b"hello", self.pub)
        data = ecc.serialize_blocks(blocks)
        self.assertEqual(ecc.deserialize_blocks(data), blocks)


class TotpTests(unittest.TestCase):
    def test_base32_roundtrip(self):
        for data in (b"", b"A", b"hello world", bytes(range(20))):
            self.assertEqual(base32_decode(base32_encode(data)), data)

    def test_base32_known_vector(self):
        self.assertEqual(base32_encode(b"hello world"), "NBSWY3DPEB3W64TMMQ======")

    def test_hotp_deterministic_and_six_digits(self):
        secret = generate_secret()
        self.assertEqual(hotp(secret, 0), hotp(secret, 0))
        self.assertNotEqual(hotp(secret, 0), hotp(secret, 1))
        self.assertEqual(len(hotp(secret, 0)), 6)

    def test_hotp_matches_rfc4226_vectors(self):
        # RFC 4226 Appendix D, secret = ASCII "12345678901234567890"
        secret = b"12345678901234567890"
        expected = ["755224", "287082", "359152", "969429", "338314"]
        for counter, code in enumerate(expected):
            self.assertEqual(hotp(secret, counter), code)

    def test_verify_totp_accepts_current_rejects_wrong(self):
        secret = generate_secret()
        code = totp(secret)
        self.assertTrue(verify_totp(secret, code))
        wrong = "000000" if code != "000000" else "111111"
        self.assertFalse(verify_totp(secret, wrong))

    def test_verify_totp_window_tolerance(self):
        secret = generate_secret()
        past_code = totp(secret, timestamp=time.time() - 30)
        self.assertTrue(verify_totp(secret, past_code, window=1))


if __name__ == "__main__":
    unittest.main()
