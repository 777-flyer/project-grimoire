"""Tests for login rate limiting, session listing/revocation, and the
dashboard task-summary aggregation."""

from django.test import Client, TestCase

from accounts.models import Role
from accounts.rate_limit import MAX_FAILED_ATTEMPTS
from accounts.registration import create_user
from crypto_core.totp import base32_encode, base32_decode, totp
from vault import services


def _totp_code(secret_b32: str) -> str:
    return totp(base32_decode(secret_b32))


def _login(client: Client, username: str, secret_b32: str, password: str):
    resp = client.post("/api/auth/login/step1", {"username": username, "password": password},
                        content_type="application/json")
    ticket = resp.json()["pending_ticket"]
    resp = client.post("/api/auth/login/step2", {"pending_ticket": ticket, "code": _totp_code(secret_b32)},
                        content_type="application/json")
    assert resp.status_code == 200, resp.content


class RateLimitTests(TestCase):
    def setUp(self):
        self.user, secret = create_user("locktest", "locktest@example.com", "", "L0ckTestPW!", Role.DEVOPS_ENGINEER)
        self.user.totp_confirmed = True
        self.user.save(update_fields=["totp_confirmed"])
        self.secret_b32 = base32_encode(secret)

    def test_lockout_after_max_failed_attempts_then_recovers_on_success(self):
        client = Client()
        for _ in range(MAX_FAILED_ATTEMPTS):
            resp = client.post("/api/auth/login/step1", {"username": "locktest", "password": "wrong"},
                                content_type="application/json")
            self.assertEqual(resp.status_code, 401)

        # next attempt, even with the correct password, is locked out
        resp = client.post("/api/auth/login/step1", {"username": "locktest", "password": "L0ckTestPW!"},
                            content_type="application/json")
        self.assertEqual(resp.status_code, 429)

        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.locked_until)

        # simulate the cooldown having elapsed
        from datetime import timedelta
        from django.utils import timezone
        self.user.locked_until = timezone.now() - timedelta(seconds=1)
        self.user.save(update_fields=["locked_until"])

        resp = client.post("/api/auth/login/step1", {"username": "locktest", "password": "L0ckTestPW!"},
                            content_type="application/json")
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_successful_login_resets_failed_counter(self):
        client = Client()
        client.post("/api/auth/login/step1", {"username": "locktest", "password": "wrong"},
                     content_type="application/json")
        client.post("/api/auth/login/step1", {"username": "locktest", "password": "wrong"},
                     content_type="application/json")
        resp = client.post("/api/auth/login/step1", {"username": "locktest", "password": "L0ckTestPW!"},
                            content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_login_attempts, 0)


class SessionManagementTests(TestCase):
    def setUp(self):
        self.user, secret = create_user("sesstest", "sesstest@example.com", "", "S3ssTestPW!", Role.DEVOPS_ENGINEER)
        self.user.totp_confirmed = True
        self.user.save(update_fields=["totp_confirmed"])
        self.secret_b32 = base32_encode(secret)

    def test_list_and_revoke_other_session(self):
        client_a = Client()
        _login(client_a, "sesstest", self.secret_b32, "S3ssTestPW!")
        client_b = Client()
        _login(client_b, "sesstest", self.secret_b32, "S3ssTestPW!")

        resp = client_a.get("/api/auth/sessions")
        self.assertEqual(resp.status_code, 200)
        sessions_list = resp.json()
        self.assertEqual(len(sessions_list), 2)

        other = next(s for s in sessions_list if not s["is_current"])
        resp = client_a.post(f"/api/auth/sessions/{other['id']}/revoke")
        self.assertEqual(resp.status_code, 200)

        # client_b's session is now dead
        resp = client_b.get("/api/auth/profile")
        self.assertEqual(resp.status_code, 401)
        # client_a is unaffected
        resp = client_a.get("/api/auth/profile")
        self.assertEqual(resp.status_code, 200)

    def test_cannot_revoke_another_users_session(self):
        other_user, other_secret = create_user("sesstest2", "sesstest2@example.com", "", "S3ssTestPW2!", Role.DEVOPS_ENGINEER)
        other_user.totp_confirmed = True
        other_user.save(update_fields=["totp_confirmed"])

        client_a = Client()
        _login(client_a, "sesstest", self.secret_b32, "S3ssTestPW!")
        client_b = Client()
        _login(client_b, "sesstest2", base32_encode(other_secret), "S3ssTestPW2!")

        resp = client_b.get("/api/auth/sessions")
        b_session_id = resp.json()[0]["id"]

        resp = client_a.post(f"/api/auth/sessions/{b_session_id}/revoke")
        self.assertEqual(resp.status_code, 404)


class TaskSummaryTests(TestCase):
    def setUp(self):
        self.admin, admin_secret = create_user("taskadmin", "taskadmin@example.com", "", "TaskAdminPW!", Role.SUPER_ADMIN)
        self.pm, pm_secret = create_user("taskpm", "taskpm@example.com", "", "TaskPmPW!!!", Role.PROJECT_MANAGER)
        self.eng, eng_secret = create_user("taskeng", "taskeng@example.com", "", "TaskEngPW!!", Role.DEVOPS_ENGINEER)
        for user in (self.admin, self.pm, self.eng):
            user.totp_confirmed = True
            user.save(update_fields=["totp_confirmed"])
        self.pm_secret_b32 = base32_encode(pm_secret)
        self.eng_secret_b32 = base32_encode(eng_secret)

        self.project = services.create_project("Task Summary Co", self.pm, self.admin)
        services.grant_access(self.project, self.eng, self.pm)

    def test_pm_sees_pending_approval_count(self):
        services.create_record(self.project, self.eng, "HOSTING", "DigitalOcean", password="x")

        pm_client = Client()
        _login(pm_client, "taskpm", self.pm_secret_b32, "TaskPmPW!!!")
        resp = pm_client.get("/api/vault/tasks-summary")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["pending_approvals"], 1)

    def test_devops_sees_own_pending_submission_count(self):
        services.create_record(self.project, self.eng, "HOSTING", "DigitalOcean", password="x")

        eng_client = Client()
        _login(eng_client, "taskeng", self.eng_secret_b32, "TaskEngPW!!")
        resp = eng_client.get("/api/vault/tasks-summary")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["my_pending_submissions"], 1)

    def test_open_issue_count(self):
        record = services.create_record(self.project, self.eng, "HOSTING", "DigitalOcean", password="x")
        services.approve_record(record, self.pm)
        services.add_note(record, self.eng, "disk almost full", kind="issue")

        eng_client = Client()
        _login(eng_client, "taskeng", self.eng_secret_b32, "TaskEngPW!!")
        resp = eng_client.get("/api/vault/tasks-summary")
        self.assertEqual(resp.json()["open_issues"], 1)
