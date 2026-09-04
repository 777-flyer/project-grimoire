"""Device fingerprint: a coarse binding of a session to the client that
created it, derived from headers that stay stable per browser/device."""

from crypto_core.sha256 import sha256


def fingerprint_from_request(request) -> str:
    user_agent = request.META.get("HTTP_USER_AGENT", "")
    accept_language = request.META.get("HTTP_ACCEPT_LANGUAGE", "")
    ip = request.META.get("REMOTE_ADDR", "")
    raw = f"{user_agent}|{accept_language}|{ip}".encode("utf-8")
    return sha256(raw).hex()
