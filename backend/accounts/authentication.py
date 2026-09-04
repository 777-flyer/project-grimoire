from rest_framework.authentication import BaseAuthentication

from .device import fingerprint_from_request
from .sessions import resolve_session


class SessionTokenAuthentication(BaseAuthentication):
    """Reads our own HMAC-backed session token (cookie or Bearer header),
    not django.contrib.auth, not DRF's token/session backends."""

    def authenticate(self, request):
        raw_token = request.COOKIES.get("grimoire_session") or self._token_from_header(request)
        if not raw_token:
            return None

        fingerprint = fingerprint_from_request(request)
        session = resolve_session(raw_token, fingerprint)
        if session is None:
            return None

        request.grimoire_session = session
        return (session.user, None)

    @staticmethod
    def _token_from_header(request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if header.startswith("Bearer "):
            return header[len("Bearer "):]
        return None

    def authenticate_header(self, request):
        # Required so DRF returns 401 (not 403) for a missing/invalid session.
        return "Bearer"
