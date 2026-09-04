from django.conf import settings

from crypto_core.hmac import constant_time_compare, hmac_sha256_hex


class IntegrityError(Exception):
    pass


def compute(data: bytes) -> str:
    return hmac_sha256_hex(settings.RECORD_HMAC_KEY, data)


def verify(data: bytes, expected_hex: str) -> None:
    actual = compute(data)
    if not constant_time_compare(actual.encode(), expected_hex.encode()):
        raise IntegrityError("record failed integrity check, possible tampering")
