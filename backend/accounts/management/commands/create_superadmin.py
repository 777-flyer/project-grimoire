"""Bootstrap the first Super Admin account (there's no django.contrib.admin
createsuperuser to reuse, and self-registration always creates a DevOps
Engineer, this command exists specifically to seed the first privileged
account for a fresh database)."""

import getpass

from crypto_core.totp import base32_encode
from django.core.management.base import BaseCommand, CommandError

from accounts.models import Role
from accounts.registration import RegistrationError, create_user
from accounts.validators import WeakPasswordError, validate_password_strength


class Command(BaseCommand):
    help = "Create the first Super Admin user."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--email", required=True)
        parser.add_argument("--contact", default="")

    def handle(self, *args, **options):
        username = options["username"]
        email = options["email"]
        contact = options["contact"]
        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            raise CommandError("passwords do not match")

        try:
            validate_password_strength(password, username=username, email=email)
        except WeakPasswordError as exc:
            raise CommandError(str(exc))

        try:
            user, totp_secret = create_user(username, email, contact, password, Role.SUPER_ADMIN)
        except RegistrationError as exc:
            raise CommandError(exc.message)

        self.stdout.write(self.style.SUCCESS(f"Created Super Admin #{user.pk}"))
        self.stdout.write(f"TOTP secret (base32): {base32_encode(totp_secret)}")
        self.stdout.write(
            "Add this to an authenticator app, then confirm it via "
            f"POST /api/auth/totp/confirm with user_id={user.pk} before logging in."
        )
