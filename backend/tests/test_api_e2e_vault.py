"""Vault workflow tests: project creation/assignment, credential approval,
change requests, notes/issues, RBAC across all four roles, the activity
feed, and access revocation triggering key rotation."""

from django.test import Client, TestCase

from accounts.models import Role
from accounts.registration import create_user
from crypto_core.totp import base32_encode, base32_decode, totp
from vault.models import AccessGrant, ApprovalStatus, KeyRotationLog


def _totp_code(secret_b32: str) -> str:
    return totp(base32_decode(secret_b32))


def _login(client: Client, username: str, secret_b32: str, password: str):
    resp = client.post("/api/auth/login/step1", {"username": username, "password": password},
                        content_type="application/json")
    ticket = resp.json()["pending_ticket"]
    resp = client.post("/api/auth/login/step2", {"pending_ticket": ticket, "code": _totp_code(secret_b32)},
                        content_type="application/json")
    assert resp.status_code == 200, resp.content


class VaultFlowTests(TestCase):
    def setUp(self):
        self.users = {}
        for username, role, password in [
            ("root", Role.SUPER_ADMIN, "R00tPassw0rd!"),
            ("pm1", Role.PROJECT_MANAGER, "PmPassw0rd!!"),
            ("pm2", Role.PROJECT_MANAGER, "PmTwoPassw0rd!"),
            ("eng1", Role.DEVOPS_ENGINEER, "EngPassw0rd!!"),
            ("dev1", Role.BACKEND_DEVELOPER, "DevPassw0rd!!"),
        ]:
            user, secret = create_user(username, f"{username}@example.com", "", password, role)
            user.totp_confirmed = True
            user.save(update_fields=["totp_confirmed"])
            self.users[username] = {"user": user, "password": password, "secret_b32": base32_encode(secret)}

    def _client_for(self, username: str) -> Client:
        info = self.users[username]
        client = Client()
        _login(client, username, info["secret_b32"], info["password"])
        return client

    def test_only_super_admin_creates_projects_with_a_pm_manager(self):
        admin = self._client_for("root")
        pm = self._client_for("pm1")
        pm1_id = self.users["pm1"]["user"].pk
        eng1_id = self.users["eng1"]["user"].pk

        # non-admin cannot create
        resp = pm.post("/api/vault/projects", {"name": "Nope", "manager_id": pm1_id}, content_type="application/json")
        self.assertEqual(resp.status_code, 403)

        # manager_id must actually be a Project Manager
        resp = admin.post("/api/vault/projects", {"name": "Bad manager", "manager_id": eng1_id},
                           content_type="application/json")
        self.assertEqual(resp.status_code, 400)

        resp = admin.post("/api/vault/projects", {"name": "Acme Corp", "manager_id": pm1_id},
                           content_type="application/json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["manager"], pm1_id)

    def test_full_credential_lifecycle_with_approvals_and_change_requests(self):
        admin = self._client_for("root")
        pm = self._client_for("pm1")
        eng = self._client_for("eng1")
        dev = self._client_for("dev1")

        pm1_id = self.users["pm1"]["user"].pk
        eng1_id = self.users["eng1"]["user"].pk
        dev1_id = self.users["dev1"]["user"].pk

        project_id = admin.post("/api/vault/projects", {"name": "Client Co", "manager_id": pm1_id},
                                 content_type="application/json").json()["id"]

        # only the assigned PM (or admin) can add members
        resp = pm.post(f"/api/vault/projects/{project_id}/grant", {"user_id": eng1_id}, content_type="application/json")
        self.assertEqual(resp.status_code, 200, resp.content)
        resp = pm.post(f"/api/vault/projects/{project_id}/grant", {"user_id": dev1_id}, content_type="application/json")
        self.assertEqual(resp.status_code, 200, resp.content)

        # a second, unrelated PM cannot manage this project
        pm2 = self._client_for("pm2")
        resp = pm2.post(f"/api/vault/projects/{project_id}/grant", {"user_id": eng1_id}, content_type="application/json")
        self.assertEqual(resp.status_code, 403)

        # backend developer cannot create records
        resp = dev.post(f"/api/vault/projects/{project_id}/records", {
            "platform_type": "HOSTING", "provider_name": "AWS",
        }, content_type="application/json")
        self.assertEqual(resp.status_code, 403)

        # devops creates a record -> pending
        resp = eng.post(f"/api/vault/projects/{project_id}/records", {
            "platform_type": "HOSTING", "provider_name": "AWS",
            "username": "root", "password": "s3cr3t!", "api_key": "AKIA...",
        }, content_type="application/json")
        self.assertEqual(resp.status_code, 201, resp.content)
        record_id = resp.json()["id"]
        self.assertEqual(resp.json()["approval_status"], ApprovalStatus.PENDING)

        # backend developer sees the record but not the secrets
        resp = dev.get(f"/api/vault/projects/{project_id}/records/{record_id}")
        self.assertEqual(resp.status_code, 200)
        fields = resp.json()["fields"]
        self.assertEqual(fields["provider_name"], "AWS")
        self.assertIsNone(fields["password"])
        self.assertIsNone(fields["api_key"])
        self.assertIsNone(fields["username"])

        # devops cannot approve their own record
        resp = eng.post(f"/api/vault/projects/{project_id}/records/{record_id}/approve", content_type="application/json")
        self.assertEqual(resp.status_code, 403)

        # PM approves
        resp = pm.post(f"/api/vault/projects/{project_id}/records/{record_id}/approve", content_type="application/json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["approval_status"], ApprovalStatus.APPROVED)

        # devops submits a change request (not auto-approved)
        resp = eng.post(f"/api/vault/projects/{project_id}/records/{record_id}/change-requests", {
            "password": "new-password-123",
        }, content_type="application/json")
        self.assertEqual(resp.status_code, 201, resp.content)
        cr_id = resp.json()["id"]
        self.assertEqual(resp.json()["status"], ApprovalStatus.PENDING)

        # record unchanged until approved
        resp = pm.get(f"/api/vault/projects/{project_id}/records/{record_id}")
        self.assertEqual(resp.json()["fields"]["password"], "s3cr3t!")

        # PM approves the change request -> applied
        resp = pm.post(
            f"/api/vault/projects/{project_id}/records/{record_id}/change-requests/{cr_id}/approve",
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        resp = pm.get(f"/api/vault/projects/{project_id}/records/{record_id}")
        self.assertEqual(resp.json()["fields"]["password"], "new-password-123")

        # PM editing directly is auto-approved (via the same change-request endpoint)
        resp = pm.post(f"/api/vault/projects/{project_id}/records/{record_id}/change-requests", {
            "provider_name": "AWS (renamed)",
        }, content_type="application/json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["status"], ApprovalStatus.APPROVED)
        resp = pm.get(f"/api/vault/projects/{project_id}/records/{record_id}")
        self.assertEqual(resp.json()["fields"]["provider_name"], "AWS (renamed)")

        # backend developer reports an issue
        resp = dev.post(f"/api/vault/projects/{project_id}/records/{record_id}/notes", {
            "text": "SSH access seems to be timing out", "kind": "issue",
        }, content_type="application/json")
        self.assertEqual(resp.status_code, 201, resp.content)
        note_id = resp.json()["id"]
        self.assertEqual(resp.json()["status"], "open")

        # backend developer cannot resolve their own issue
        resp = dev.post(f"/api/vault/projects/{project_id}/records/{record_id}/notes/{note_id}/resolve",
                         content_type="application/json")
        self.assertEqual(resp.status_code, 403)

        # devops resolves it
        resp = eng.post(f"/api/vault/projects/{project_id}/records/{record_id}/notes/{note_id}/resolve",
                         content_type="application/json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["status"], "resolved")

        # the feed captured the whole story
        resp = pm.get(f"/api/vault/projects/{project_id}/feed")
        self.assertEqual(resp.status_code, 200)
        event_types = [e["event_type"] for e in resp.json()]
        for expected in (
            "PROJECT_CREATED", "MEMBER_ADDED", "RECORD_REQUESTED", "RECORD_APPROVED",
            "CHANGE_REQUESTED", "CHANGE_APPROVED", "ISSUE_REPORTED", "ISSUE_RESOLVED",
        ):
            self.assertIn(expected, event_types)

    def test_rotation_keeps_change_requests_and_feed_decryptable(self):
        """Regression test: key rotation must re-encrypt ChangeRequest and
        FeedEvent rows too, not just CredentialRecord/Project, or anything
        logged/proposed before the rotation becomes permanently undecryptable
        (crypto_core.rsa.OAEPError) the next time it's read."""
        admin = self._client_for("root")
        pm = self._client_for("pm1")
        eng = self._client_for("eng1")
        pm1_id = self.users["pm1"]["user"].pk
        eng1_id = self.users["eng1"]["user"].pk

        project_id = admin.post("/api/vault/projects", {"name": "Rotation Test", "manager_id": pm1_id},
                                 content_type="application/json").json()["id"]
        pm.post(f"/api/vault/projects/{project_id}/grant", {"user_id": eng1_id}, content_type="application/json")

        record_id = pm.post(f"/api/vault/projects/{project_id}/records", {
            "platform_type": "HOSTING", "provider_name": "Linode", "password": "orig-pw",
        }, content_type="application/json").json()["id"]

        # a pending change request that will NOT be applied before rotation,
        # so its ciphertext is only ever encrypted under the pre-rotation key
        resp = eng.post(f"/api/vault/projects/{project_id}/records/{record_id}/change-requests", {
            "password": "proposed-pw",
        }, content_type="application/json")
        cr_id = resp.json()["id"]

        resp = pm.post(f"/api/vault/projects/{project_id}/rotate", content_type="application/json")
        self.assertEqual(resp.status_code, 200, resp.content)

        # both reads must survive the rotation without an integrity/decrypt error
        resp = pm.get(f"/api/vault/projects/{project_id}/records/{record_id}/change-requests")
        self.assertEqual(resp.status_code, 200, resp.content)
        cr = next(c for c in resp.json() if c["id"] == cr_id)
        self.assertIsNone(cr["error"])
        self.assertEqual(cr["proposed"]["password"], "proposed-pw")

        resp = pm.get(f"/api/vault/projects/{project_id}/feed")
        self.assertEqual(resp.status_code, 200, resp.content)
        for event in resp.json():
            self.assertNotEqual(event["message"], "<integrity check failed>")

    def test_revoke_access_rotates_key_and_removes_access(self):
        admin = self._client_for("root")
        pm = self._client_for("pm1")
        eng = self._client_for("eng1")
        pm1_id = self.users["pm1"]["user"].pk
        eng1_id = self.users["eng1"]["user"].pk

        project_id = admin.post("/api/vault/projects", {"name": "Revoke Test", "manager_id": pm1_id},
                                 content_type="application/json").json()["id"]
        pm.post(f"/api/vault/projects/{project_id}/grant", {"user_id": eng1_id}, content_type="application/json")

        resp = eng.post(f"/api/vault/projects/{project_id}/records", {
            "platform_type": "DOMAIN", "provider_name": "GoDaddy", "username": "u", "password": "p",
        }, content_type="application/json")
        record_id = resp.json()["id"]

        rotations_before = KeyRotationLog.objects.filter(scope_id=project_id).count()
        resp = pm.post(f"/api/vault/projects/{project_id}/revoke", {"user_id": eng1_id}, content_type="application/json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(KeyRotationLog.objects.filter(scope_id=project_id).count(), rotations_before + 1)
        self.assertFalse(AccessGrant.objects.filter(project_id=project_id, user_id=eng1_id, revoked_at__isnull=True).exists())

        resp = eng.get(f"/api/vault/projects/{project_id}/records")
        self.assertEqual(resp.status_code, 403)

        # PM still has access and data survived re-encryption
        resp = pm.get(f"/api/vault/projects/{project_id}/records/{record_id}")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["fields"]["provider_name"], "GoDaddy")

    def test_admin_can_create_users_with_any_role(self):
        admin = self._client_for("root")
        resp = admin.post("/api/auth/admin/users/create", {
            "username": "newpm", "email": "newpm@example.com", "password": "Xk9$vBra!nch2",
            "role": Role.PROJECT_MANAGER,
        }, content_type="application/json")
        self.assertEqual(resp.status_code, 201, resp.content)

    def test_non_admin_cannot_provision_users(self):
        pm = self._client_for("pm1")
        resp = pm.post("/api/auth/admin/users/create", {
            "username": "sneaky", "email": "sneaky@example.com", "password": "Sneaky1!Pass",
            "role": Role.SUPER_ADMIN,
        }, content_type="application/json")
        self.assertEqual(resp.status_code, 403)

    def test_create_record_with_environment_and_expiry(self):
        admin = self._client_for("root")
        pm = self._client_for("pm1")
        pm1_id = self.users["pm1"]["user"].pk

        project_id = admin.post("/api/vault/projects", {"name": "Env Test Co", "manager_id": pm1_id},
                                 content_type="application/json").json()["id"]

        resp = pm.post(f"/api/vault/projects/{project_id}/records", {
            "platform_type": "DOMAIN", "provider_name": "Namecheap",
            "environment": "STAGING", "expires_on": "2020-01-01",
        }, content_type="application/json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["environment"], "STAGING")
        self.assertEqual(resp.json()["expires_on"], "2020-01-01")

    def test_devops_can_update_metadata_but_backend_dev_cannot(self):
        admin = self._client_for("root")
        pm = self._client_for("pm1")
        eng = self._client_for("eng1")
        dev = self._client_for("dev1")
        pm1_id = self.users["pm1"]["user"].pk
        eng1_id = self.users["eng1"]["user"].pk
        dev1_id = self.users["dev1"]["user"].pk

        project_id = admin.post("/api/vault/projects", {"name": "Metadata Co", "manager_id": pm1_id},
                                 content_type="application/json").json()["id"]
        pm.post(f"/api/vault/projects/{project_id}/grant", {"user_id": eng1_id}, content_type="application/json")
        pm.post(f"/api/vault/projects/{project_id}/grant", {"user_id": dev1_id}, content_type="application/json")

        record_id = pm.post(f"/api/vault/projects/{project_id}/records", {
            "platform_type": "HOSTING", "provider_name": "Linode",
        }, content_type="application/json").json()["id"]

        resp = eng.post(f"/api/vault/projects/{project_id}/records/{record_id}/metadata", {
            "environment": "DEVELOPMENT", "expires_on": "2030-06-15",
        }, content_type="application/json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["environment"], "DEVELOPMENT")
        self.assertEqual(resp.json()["expires_on"], "2030-06-15")

        resp = dev.post(f"/api/vault/projects/{project_id}/records/{record_id}/metadata", {
            "environment": "PRODUCTION",
        }, content_type="application/json")
        self.assertEqual(resp.status_code, 403)

    def test_filter_records_by_platform_and_environment(self):
        admin = self._client_for("root")
        pm = self._client_for("pm1")
        pm1_id = self.users["pm1"]["user"].pk

        project_id = admin.post("/api/vault/projects", {"name": "Filter Co", "manager_id": pm1_id},
                                 content_type="application/json").json()["id"]
        pm.post(f"/api/vault/projects/{project_id}/records", {
            "platform_type": "DOMAIN", "provider_name": "GoDaddy", "environment": "PRODUCTION",
        }, content_type="application/json")
        pm.post(f"/api/vault/projects/{project_id}/records", {
            "platform_type": "EMAIL", "provider_name": "Google Workspace", "environment": "STAGING",
        }, content_type="application/json")

        resp = pm.get(f"/api/vault/projects/{project_id}/records?platform_type=DOMAIN")
        self.assertEqual(len(resp.json()), 1)
        self.assertEqual(resp.json()[0]["fields"]["provider_name"], "GoDaddy")

        resp = pm.get(f"/api/vault/projects/{project_id}/records?environment=STAGING")
        self.assertEqual(len(resp.json()), 1)
        self.assertEqual(resp.json()[0]["fields"]["provider_name"], "Google Workspace")

    def test_task_summary_includes_expiring_soon(self):
        admin = self._client_for("root")
        pm = self._client_for("pm1")
        pm1_id = self.users["pm1"]["user"].pk

        project_id = admin.post("/api/vault/projects", {"name": "Expiry Co", "manager_id": pm1_id},
                                 content_type="application/json").json()["id"]

        from datetime import date, timedelta
        soon = (date.today() + timedelta(days=5)).isoformat()
        far = (date.today() + timedelta(days=400)).isoformat()

        pm.post(f"/api/vault/projects/{project_id}/records", {
            "platform_type": "DOMAIN", "provider_name": "ExpiringSoon.com", "expires_on": soon,
        }, content_type="application/json")
        pm.post(f"/api/vault/projects/{project_id}/records", {
            "platform_type": "DOMAIN", "provider_name": "FarAway.com", "expires_on": far,
        }, content_type="application/json")

        resp = pm.get("/api/vault/tasks-summary")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["expiring_soon"], 1)

    def test_password_rotation_tracked_on_create_and_change(self):
        admin = self._client_for("root")
        pm = self._client_for("pm1")
        eng = self._client_for("eng1")
        pm1_id = self.users["pm1"]["user"].pk
        eng1_id = self.users["eng1"]["user"].pk

        project_id = admin.post("/api/vault/projects", {"name": "Rotation Track Co", "manager_id": pm1_id},
                                 content_type="application/json").json()["id"]
        pm.post(f"/api/vault/projects/{project_id}/grant", {"user_id": eng1_id}, content_type="application/json")

        resp = pm.post(f"/api/vault/projects/{project_id}/records", {
            "platform_type": "HOSTING", "provider_name": "DigitalOcean", "password": "initial-pw",
        }, content_type="application/json")
        record_id = resp.json()["id"]
        self.assertIsNotNone(resp.json()["password_rotation"]["days_since_rotation"])
        self.assertEqual(resp.json()["password_rotation"]["tone"], "success")

        # PM edits directly (auto-approved change) with a DIFFERENT password -> stamps rotation again
        resp = pm.post(f"/api/vault/projects/{project_id}/records/{record_id}/change-requests", {
            "provider_name": "DigitalOcean",  # unchanged field, should not matter
        }, content_type="application/json")
        self.assertEqual(resp.status_code, 201)

        resp = pm.get(f"/api/vault/projects/{project_id}/records/{record_id}")
        first_days = resp.json()["password_rotation"]["days_since_rotation"]

        resp = pm.post(f"/api/vault/projects/{project_id}/records/{record_id}/change-requests", {
            "password": "rotated-pw",
        }, content_type="application/json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["status"], ApprovalStatus.APPROVED)

        resp = pm.get(f"/api/vault/projects/{project_id}/records/{record_id}")
        self.assertIsNotNone(resp.json()["password_rotation"]["days_since_rotation"])
        # still fresh (0 days) even though the earlier no-op change request didn't reset it
        self.assertLessEqual(resp.json()["password_rotation"]["days_since_rotation"], first_days)

    def test_access_log_records_reveal_and_copy_and_is_manager_only(self):
        admin = self._client_for("root")
        pm = self._client_for("pm1")
        eng = self._client_for("eng1")
        dev = self._client_for("dev1")
        pm1_id = self.users["pm1"]["user"].pk
        eng1_id = self.users["eng1"]["user"].pk
        dev1_id = self.users["dev1"]["user"].pk

        project_id = admin.post("/api/vault/projects", {"name": "Audit Co", "manager_id": pm1_id},
                                 content_type="application/json").json()["id"]
        pm.post(f"/api/vault/projects/{project_id}/grant", {"user_id": eng1_id}, content_type="application/json")
        pm.post(f"/api/vault/projects/{project_id}/grant", {"user_id": dev1_id}, content_type="application/json")

        record_id = pm.post(f"/api/vault/projects/{project_id}/records", {
            "platform_type": "HOSTING", "provider_name": "Vultr", "password": "hunter2",
        }, content_type="application/json").json()["id"]

        resp = eng.post(f"/api/vault/projects/{project_id}/records/{record_id}/access-log", {
            "field_name": "password", "action": "REVEAL",
        }, content_type="application/json")
        self.assertEqual(resp.status_code, 201, resp.content)

        # a Backend Developer can log their own access...
        resp = dev.post(f"/api/vault/projects/{project_id}/records/{record_id}/access-log", {
            "field_name": "username", "action": "COPY",
        }, content_type="application/json")
        self.assertEqual(resp.status_code, 201)

        # ...but cannot read the audit trail themselves
        resp = dev.get(f"/api/vault/projects/{project_id}/records/{record_id}/access-log")
        self.assertEqual(resp.status_code, 403)

        resp = pm.get(f"/api/vault/projects/{project_id}/records/{record_id}/access-log")
        self.assertEqual(resp.status_code, 200)
        entries = resp.json()
        self.assertEqual(len(entries), 2)
        self.assertEqual({e["field_name"] for e in entries}, {"password", "username"})

    def test_task_summary_flags_overdue_password_rotation(self):
        from datetime import timedelta
        from django.utils import timezone as dj_timezone

        admin = self._client_for("root")
        pm = self._client_for("pm1")
        pm1_id = self.users["pm1"]["user"].pk

        project_id = admin.post("/api/vault/projects", {"name": "Overdue Co", "manager_id": pm1_id},
                                 content_type="application/json").json()["id"]
        record_id = pm.post(f"/api/vault/projects/{project_id}/records", {
            "platform_type": "HOSTING", "provider_name": "Hetzner", "password": "old-pw",
        }, content_type="application/json").json()["id"]

        from vault.models import CredentialRecord
        record = CredentialRecord.objects.get(pk=record_id)
        record.password_last_rotated = dj_timezone.now() - timedelta(days=120)
        record.save(update_fields=["password_last_rotated"])

        resp = pm.get("/api/vault/tasks-summary")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["passwords_overdue_rotation"], 1)
