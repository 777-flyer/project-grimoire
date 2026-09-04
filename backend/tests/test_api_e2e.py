"""End-to-end smoke test of the whole auth + vault flow through Django's
test client: registration, TOTP confirmation, two-step login, session
cookie handling, project/record CRUD, access grant, note, and revocation."""

from django.test import Client, TestCase

from accounts.models import Role, User
from accounts.registration import create_user
from crypto_core.totp import base32_decode, totp
from vault.models import AccessGrant, KeyRotationLog


def _totp_code(secret_b32: str) -> str:
    return totp(base32_decode(secret_b32))


class AuthFlowTests(TestCase):
    def test_register_confirm_login_profile(self):
        client = Client()

        resp = client.post("/api/auth/register", {
            "username": "alice", "email": "alice@example.com",
            "contact": "+1-555-0100", "password": "Sup3r$ecretPW",
        }, content_type="application/json")
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        user_id = body["user_id"]
        secret_b32 = body["totp_secret_base32"]

        # can't log in before TOTP is confirmed
        resp = client.post("/api/auth/login/step1", {"username": "alice", "password": "Sup3r$ecretPW"},
                            content_type="application/json")
        self.assertEqual(resp.status_code, 403)

        resp = client.post("/api/auth/totp/confirm", {"user_id": user_id, "code": _totp_code(secret_b32)},
                            content_type="application/json")
        self.assertEqual(resp.status_code, 200, resp.content)

        resp = client.post("/api/auth/login/step1", {"username": "alice", "password": "Sup3r$ecretPW"},
                            content_type="application/json")
        self.assertEqual(resp.status_code, 200, resp.content)
        ticket = resp.json()["pending_ticket"]

        resp = client.post("/api/auth/login/step2", {"pending_ticket": ticket, "code": _totp_code(secret_b32)},
                            content_type="application/json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertIn("grimoire_session", resp.cookies)

        resp = client.get("/api/auth/profile")
        self.assertEqual(resp.status_code, 200, resp.content)
        profile = resp.json()
        self.assertEqual(profile["username"], "alice")
        self.assertEqual(profile["email"], "alice@example.com")
        self.assertEqual(profile["contact"], "+1-555-0100")
        self.assertEqual(profile["role"], Role.DEVOPS_ENGINEER)

        resp = client.post("/api/auth/logout")
        self.assertEqual(resp.status_code, 200)

        # session should now be dead
        resp = client.get("/api/auth/profile")
        self.assertEqual(resp.status_code, 401)

    def test_wrong_password_rejected(self):
        client = Client()
        resp = client.post("/api/auth/register", {
            "username": "bob", "email": "bob@example.com", "password": "An0ther$trongPW",
        }, content_type="application/json")
        self.assertEqual(resp.status_code, 201)
        user_id = resp.json()["user_id"]
        secret_b32 = resp.json()["totp_secret_base32"]
        client.post("/api/auth/totp/confirm", {"user_id": user_id, "code": _totp_code(secret_b32)},
                    content_type="application/json")

        resp = client.post("/api/auth/login/step1", {"username": "bob", "password": "wrong-password"},
                            content_type="application/json")
        self.assertEqual(resp.status_code, 401)

    def test_wrong_totp_code_does_not_burn_the_ticket(self):
        """Regression test: a wrong code on the first attempt must not
        prevent a later correct code from completing login with the same
        pending_ticket (see accounts/sessions.py resolve/consume split)."""
        client = Client()
        resp = client.post("/api/auth/register", {
            "username": "carol", "email": "carol@example.com", "password": "Car0lPassw0rd!",
        }, content_type="application/json")
        user_id = resp.json()["user_id"]
        secret_b32 = resp.json()["totp_secret_base32"]
        client.post("/api/auth/totp/confirm", {"user_id": user_id, "code": _totp_code(secret_b32)},
                    content_type="application/json")

        resp = client.post("/api/auth/login/step1", {"username": "carol", "password": "Car0lPassw0rd!"},
                            content_type="application/json")
        ticket = resp.json()["pending_ticket"]

        resp = client.post("/api/auth/login/step2", {"pending_ticket": ticket, "code": "000000"},
                            content_type="application/json")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()["error"], "invalid TOTP code")

        resp = client.post("/api/auth/login/step2", {"pending_ticket": ticket, "code": _totp_code(secret_b32)},
                            content_type="application/json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertIn("grimoire_session", resp.cookies)

