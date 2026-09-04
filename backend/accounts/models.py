from django.db import models


class Role(models.TextChoices):
    SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
    PROJECT_MANAGER = "PROJECT_MANAGER", "Project Manager"
    DEVOPS_ENGINEER = "DEVOPS_ENGINEER", "DevOps Engineer"
    BACKEND_DEVELOPER = "BACKEND_DEVELOPER", "Backend Developer"


class User(models.Model):
    """Custom user model; no relation to django.contrib.auth."""

    # HMAC blind index for lookup, since username_enc/email_enc are randomized ciphertext.
    username_lookup = models.CharField(max_length=64, unique=True, db_index=True)
    email_lookup = models.CharField(max_length=64, unique=True, db_index=True)

    username_enc = models.BinaryField()
    email_enc = models.BinaryField()
    contact_enc = models.BinaryField(blank=True, default=b"")
    profile_hmac = models.CharField(max_length=64)  # HMAC-SHA256 over the three fields above

    password_hash = models.BinaryField()
    password_salt = models.BinaryField()

    # Personal keypair; also receives EC-ElGamal-wrapped project-key grants.
    rsa_pub_n = models.TextField()
    rsa_pub_e = models.BigIntegerField(default=65537)
    rsa_priv_wrapped = models.BinaryField()  # wrapped under the master key

    ecc_pub_x = models.TextField()
    ecc_pub_y = models.TextField()
    ecc_priv_wrapped = models.BinaryField()  # wrapped under the master key

    totp_secret_wrapped = models.BinaryField()
    totp_confirmed = models.BooleanField(default=False)

    role = models.CharField(max_length=20, choices=Role.choices)

    # Login rate limiting.
    failed_login_attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_user"

    def __str__(self):
        return f"User#{self.pk} ({self.role})"


class PendingLogin(models.Model):
    """Short-lived ticket issued after primary-credential success, consumed
    once TOTP verifies."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="pending_logins")
    ticket_hmac = models.CharField(max_length=64, unique=True, db_index=True)
    device_fingerprint = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "accounts_pending_login"


class Session(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    token_hmac = models.CharField(max_length=64, unique=True, db_index=True)
    device_fingerprint = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "accounts_session"
