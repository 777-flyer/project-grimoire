from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from crypto_core.totp import base32_encode, verify_totp

from . import blind_index, keys, passwords, profile, rate_limit, sessions
from .authentication import SessionTokenAuthentication
from .device import fingerprint_from_request
from .models import Role, Session, User
from .permissions import IsAuthenticated, IsSuperAdmin
from .registration import RegistrationError, create_user
from .validators import WeakPasswordError, validate_password_strength

SESSION_COOKIE_NAME = "grimoire_session"


def _set_session_cookie(response: Response, raw_token: str):
    response.set_cookie(
        SESSION_COOKIE_NAME,
        raw_token,
        httponly=True,
        samesite="Strict",
        secure=False,  # flip to True once served over HTTPS
        max_age=1800,
    )


class RegisterView(APIView):
    """Public self-registration; always creates a DevOps Engineer account."""

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        data = request.data
        username = (data.get("username") or "").strip()
        email = (data.get("email") or "").strip()
        contact = (data.get("contact") or "").strip()
        password = data.get("password") or ""

        if not username or not email or not password:
            return Response({"error": "username, email, and password are required"}, status=400)

        try:
            validate_password_strength(password, username=username, email=email)
        except WeakPasswordError as exc:
            return Response({"error": str(exc)}, status=400)

        try:
            user, totp_secret = create_user(username, email, contact, password, Role.DEVOPS_ENGINEER)
        except RegistrationError as exc:
            return Response({"error": exc.message}, status=exc.status)

        return Response(
            {
                "user_id": user.pk,
                "totp_secret_base32": base32_encode(totp_secret),
                "totp_issuer": "Grimoire",
                "message": "Scan the TOTP secret into an authenticator app, then confirm with /api/auth/totp/confirm before logging in.",
            },
            status=201,
        )


class AdminCreateUserView(APIView):
    """Super Admin provisions accounts for any role directly."""

    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        data = request.data
        username = (data.get("username") or "").strip()
        email = (data.get("email") or "").strip()
        contact = (data.get("contact") or "").strip()
        password = data.get("password") or ""
        role = data.get("role") or ""

        if role not in Role.values:
            return Response({"error": f"role must be one of {Role.values}"}, status=400)
        if not username or not email or not password:
            return Response({"error": "username, email, and password are required"}, status=400)

        try:
            validate_password_strength(password, username=username, email=email)
        except WeakPasswordError as exc:
            return Response({"error": str(exc)}, status=400)

        try:
            user, totp_secret = create_user(username, email, contact, password, role)
        except RegistrationError as exc:
            return Response({"error": exc.message}, status=exc.status)

        return Response(
            {
                "user_id": user.pk,
                "role": user.role,
                "totp_secret_base32": base32_encode(totp_secret),
            },
            status=201,
        )


class AdminListUsersView(APIView):
    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        users = User.objects.all().order_by("-created_at")
        results = []
        for user in users:
            try:
                fields = profile.decrypt_profile_fields(user)
            except profile.ProfileIntegrityError:
                fields = {"username": "<integrity check failed>", "email": "", "contact": ""}
            results.append({
                "id": user.pk,
                "role": user.role,
                "is_active": user.is_active,
                "totp_confirmed": user.totp_confirmed,
                "created_at": user.created_at,
                **fields,
            })
        return Response(results)


class UserLookupView(APIView):
    """Resolve a username to a user id via the blind index, without
    decrypting rows."""

    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        username = (request.query_params.get("username") or "").strip()
        if not username:
            return Response({"error": "username query param is required"}, status=400)
        try:
            user = User.objects.get(username_lookup=blind_index.compute(username))
        except User.DoesNotExist:
            return Response({"error": "no such user"}, status=404)
        return Response({"id": user.pk, "username": username, "role": user.role})


class ConfirmTotpView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        user_id = request.data.get("user_id")
        code = request.data.get("code")
        if not user_id or not code:
            return Response({"error": "user_id and code are required"}, status=400)

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"error": "invalid user"}, status=404)

        if user.totp_confirmed:
            return Response({"error": "TOTP already confirmed"}, status=409)

        secret = keys.get_totp_secret(user)
        if not verify_totp(secret, code):
            return Response({"error": "invalid code"}, status=400)

        user.totp_confirmed = True
        user.save(update_fields=["totp_confirmed"])
        return Response({"message": "TOTP confirmed, you can now log in."})


class LoginStep1View(APIView):
    """Primary-credential check; issues a pending-login ticket, not a session."""

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        username = (request.data.get("username") or "").strip()
        password = request.data.get("password") or ""
        if not username or not password:
            return Response({"error": "username and password are required"}, status=400)

        try:
            user = User.objects.get(username_lookup=blind_index.compute(username))
        except User.DoesNotExist:
            return Response({"error": "invalid credentials"}, status=401)

        if rate_limit.is_locked(user):
            wait = rate_limit.lockout_remaining_seconds(user)
            return Response(
                {"error": f"too many failed attempts, try again in {wait // 60 + 1} minute(s)"}, status=429
            )

        if not user.is_active or not passwords.verify_password(password, bytes(user.password_hash), bytes(user.password_salt)):
            rate_limit.register_failed_attempt(user)
            return Response({"error": "invalid credentials"}, status=401)

        rate_limit.register_successful_attempt(user)

        if not user.totp_confirmed:
            return Response({"error": "TOTP setup not completed for this account"}, status=403)

        fingerprint = fingerprint_from_request(request)
        ticket = sessions.create_pending_login(user, fingerprint)
        return Response({"pending_ticket": ticket, "message": "Enter your TOTP code to complete login."})


class LoginStep2View(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        ticket = request.data.get("pending_ticket")
        code = request.data.get("code")
        if not ticket or not code:
            return Response({"error": "pending_ticket and code are required"}, status=400)

        fingerprint = fingerprint_from_request(request)
        pending = sessions.resolve_pending_login(ticket, fingerprint)
        if pending is None:
            return Response({"error": "pending login expired or invalid"}, status=401)

        user = pending.user
        secret = keys.get_totp_secret(user)
        if not verify_totp(secret, code):
            return Response({"error": "invalid TOTP code"}, status=401)

        sessions.consume_pending_login(pending)
        raw_token = sessions.create_session(user, fingerprint)
        response = Response({"message": "logged in", "role": user.role})
        _set_session_cookie(response, raw_token)
        return response


class LogoutView(APIView):
    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        sessions.revoke_session(request.grimoire_session)
        response = Response({"message": "logged out"})
        response.delete_cookie(SESSION_COOKIE_NAME)
        return response


class SessionListView(APIView):
    """Lists every active session for the current user."""

    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        active = request.user.sessions.filter(revoked_at__isnull=True, expires_at__gt=timezone.now()).order_by("-created_at")
        return Response([
            {
                "id": s.pk,
                "device_label": s.device_fingerprint[:12],
                "created_at": s.created_at,
                "expires_at": s.expires_at,
                "is_current": request.grimoire_session is not None and s.pk == request.grimoire_session.pk,
            }
            for s in active
        ])


class SessionRevokeView(APIView):
    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        session = get_object_or_404(Session, pk=session_id, user=request.user)
        was_current = request.grimoire_session is not None and session.pk == request.grimoire_session.pk
        sessions.revoke_session(session)
        response = Response({"message": "session revoked"})
        if was_current:
            response.delete_cookie(SESSION_COOKIE_NAME)
        return response


class ProfileView(APIView):
    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            fields = profile.decrypt_profile_fields(request.user)
        except profile.ProfileIntegrityError:
            return Response({"error": "profile integrity check failed"}, status=500)
        fields["role"] = request.user.role
        fields["id"] = request.user.pk
        return Response(fields)

    def put(self, request):
        username = request.data.get("username")
        email = request.data.get("email")
        contact = request.data.get("contact")
        if not username or not email:
            return Response({"error": "username and email are required"}, status=400)

        user = request.user
        rsa_pub = keys.get_rsa_public(user)
        new_fields = profile.encrypt_profile_fields(rsa_pub, username, email, contact or "")
        user.username_lookup = blind_index.compute(username)
        user.email_lookup = blind_index.compute(email)
        for field, value in new_fields.items():
            setattr(user, field, value)
        user.updated_at = timezone.now()
        try:
            user.save()
        except IntegrityError:
            return Response({"error": "username or email already taken"}, status=409)
        return Response({"message": "profile updated"})
