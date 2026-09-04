from django.db import models

from accounts.models import User


class Project(models.Model):
    """Owns its own RSA-2048 keypair; every CredentialRecord under it is
    encrypted with this key, not any individual user's personal key."""

    name_enc = models.BinaryField()
    name_hmac = models.CharField(max_length=64)

    rsa_pub_n = models.TextField()
    rsa_pub_e = models.BigIntegerField(default=65537)
    rsa_priv_wrapped = models.BinaryField()  # wrapped under the master key; the server's operational copy

    manager = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="managed_projects"
    )  # the Project Manager the Super Admin assigned this project to

    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="projects_created")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vault_project"


class PlatformType(models.TextChoices):
    DOMAIN = "DOMAIN", "Domain"
    HOSTING = "HOSTING", "Hosting"
    EMAIL = "EMAIL", "Email"
    OTHER = "OTHER", "Other"


class ApprovalStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"


class Environment(models.TextChoices):
    PRODUCTION = "PRODUCTION", "Production"
    STAGING = "STAGING", "Staging"
    DEVELOPMENT = "DEVELOPMENT", "Development"


class CredentialRecord(models.Model):
    """A purchased credential (domain, hosting, email, etc.) for a project.
    Secret fields live in `fields_enc`, RSA-OAEP encrypted under the
    project's key with an HMAC tag. New records start PENDING until
    approved; approved records are edited via ChangeRequest."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="records")
    platform_type = models.CharField(max_length=10, choices=PlatformType.choices)
    environment = models.CharField(max_length=12, choices=Environment.choices, default=Environment.PRODUCTION)
    expires_on = models.DateField(null=True, blank=True)

    # When the password field last actually changed value, for rotation-age tracking.
    password_last_rotated = models.DateTimeField(null=True, blank=True)

    fields_enc = models.BinaryField()
    hmac_tag = models.CharField(max_length=64)

    approval_status = models.CharField(max_length=10, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING)
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="records_reviewed"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="records_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vault_credential_record"


class ChangeRequest(models.Model):
    """A proposed edit to an approved CredentialRecord, applied once
    approved. Auto-approved when the submitter already has approval authority."""

    record = models.ForeignKey(CredentialRecord, on_delete=models.CASCADE, related_name="change_requests")
    proposed_fields_enc = models.BinaryField()
    proposed_hmac = models.CharField(max_length=64)

    status = models.CharField(max_length=10, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING)
    submitted_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="change_requests_submitted")
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="change_requests_reviewed"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vault_change_request"


class AccessGrant(models.Model):
    """Grants project access by EC-ElGamal-wrapping the project's RSA
    private key to the user's personal ECC public key."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="grants")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="access_grants")
    wrapped_project_privkey = models.BinaryField()

    granted_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="grants_issued")
    granted_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "vault_access_grant"
        constraints = [
            models.UniqueConstraint(
                fields=["project", "user"],
                condition=models.Q(revoked_at__isnull=True),
                name="unique_active_grant_per_project_user",
            )
        ]


class KeyRotationLog(models.Model):
    class Scope(models.TextChoices):
        USER = "USER", "User"
        PROJECT = "PROJECT", "Project"

    class Reason(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Scheduled rotation"
        REVOCATION = "REVOCATION", "Access revocation"
        MANUAL = "MANUAL", "Manual trigger"

    scope = models.CharField(max_length=10, choices=Scope.choices)
    scope_id = models.PositiveIntegerField()
    reason = models.CharField(max_length=12, choices=Reason.choices)
    previous_key_fingerprint = models.CharField(max_length=64)
    rotated_at = models.DateTimeField(auto_now_add=True)
    rotated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="rotations_triggered")

    class Meta:
        db_table = "vault_key_rotation_log"


class FeedEventType(models.TextChoices):
    PROJECT_CREATED = "PROJECT_CREATED", "Project created"
    MEMBER_ADDED = "MEMBER_ADDED", "Member added"
    MEMBER_REVOKED = "MEMBER_REVOKED", "Member revoked"
    RECORD_REQUESTED = "RECORD_REQUESTED", "Record requested"
    RECORD_APPROVED = "RECORD_APPROVED", "Record approved"
    RECORD_REJECTED = "RECORD_REJECTED", "Record rejected"
    RECORD_EDITED = "RECORD_EDITED", "Record edited"
    CHANGE_REQUESTED = "CHANGE_REQUESTED", "Change requested"
    CHANGE_APPROVED = "CHANGE_APPROVED", "Change approved"
    CHANGE_REJECTED = "CHANGE_REJECTED", "Change rejected"
    ISSUE_REPORTED = "ISSUE_REPORTED", "Issue reported"
    ISSUE_RESOLVED = "ISSUE_RESOLVED", "Issue resolved"
    NOTE_ADDED = "NOTE_ADDED", "Note added"
    KEY_ROTATED = "KEY_ROTATED", "Key rotated"


class FeedEvent(models.Model):
    """One entry in a project's activity feed. Messages never embed a
    secret value, so the feed is safe for every role. Encrypted under the
    project's key like everything else."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="feed_events")
    record = models.ForeignKey(
        CredentialRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name="feed_events"
    )
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="feed_events")
    event_type = models.CharField(max_length=20, choices=FeedEventType.choices)

    message_enc = models.BinaryField()
    message_hmac = models.CharField(max_length=64)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vault_feed_event"
        ordering = ["-created_at"]


class AccessAction(models.TextChoices):
    REVEAL = "REVEAL", "Revealed"
    COPY = "COPY", "Copied"


class RecordAccessLog(models.Model):
    """Who revealed or copied a specific secret field, and when. Only an
    explicit reveal/copy counts, not a list view or metadata edit."""

    record = models.ForeignKey(CredentialRecord, on_delete=models.CASCADE, related_name="access_logs")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="record_access_logs")
    field_name = models.CharField(max_length=20)  # "username" | "password" | "api_key"
    action = models.CharField(max_length=10, choices=AccessAction.choices)
    accessed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vault_record_access_log"
        ordering = ["-accessed_at"]
