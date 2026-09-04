"""
Django settings for the Grimoire backend.

Deliberately does NOT install django.contrib.admin, django.contrib.auth, or
django.contrib.sessions: this project rolls its own User model, its own
from-scratch password hashing (PBKDF2, crypto_core/pbkdf2.py) and its own
HMAC-signed session tokens (accounts/sessions.py) rather than Django's
built-ins, since the assignment requires everything crypto-related to be
hand-implemented. There is no /admin/. Super Admin functionality is just
regular RBAC-gated API endpoints/pages like everything else, not a separate
privileged interface bolted on by the framework.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key-override-in-.env")
DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "accounts",
    "vault",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "grimoire.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "grimoire.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = []  # password strength is enforced in accounts/validators.py, not Django's auth app

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Grimoire-specific settings ---

# Frontend origin(s) allowed to call this API (Next.js dev server by default).
CORS_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ALLOWED_ORIGINS", "http://localhost:3000"
).split(",")
CORS_ALLOW_CREDENTIALS = True

# The master keypair's private half never lives in the DB. It's generated once
# (scripts/generate_master_key.py) and its private key stored only here, as an
# env var, loaded into memory at process start. Every User/Project RSA and ECC
# private key is RSA-OAEP-chunk-encrypted to MASTER_PUBLIC_KEY_N/E before being
# written to the DB, and decrypted with MASTER_PRIVATE_KEY_D only in memory.
MASTER_PUBLIC_KEY_N = int(os.environ["MASTER_PUBLIC_KEY_N"]) if os.environ.get("MASTER_PUBLIC_KEY_N") else None
MASTER_PUBLIC_KEY_E = int(os.environ.get("MASTER_PUBLIC_KEY_E", "65537"))
MASTER_PRIVATE_KEY_D = int(os.environ["MASTER_PRIVATE_KEY_D"]) if os.environ.get("MASTER_PRIVATE_KEY_D") else None

SESSION_TOKEN_LIFETIME_SECONDS = int(os.environ.get("SESSION_TOKEN_LIFETIME_SECONDS", 60 * 30))
SESSION_SIGNING_KEY = os.environ.get("SESSION_SIGNING_KEY", "dev-only-session-hmac-key-override-in-.env").encode()

# HMAC key for CredentialRecord/Project tamper-detection tags (the MAC requirement).
RECORD_HMAC_KEY = os.environ.get("RECORD_HMAC_KEY", "dev-only-record-hmac-key-override-in-.env").encode()

# HMAC key for deterministic "blind index" lookups (e.g. find a user by username
# at login time without decrypting every row). OAEP encryption is randomized,
# so username_enc can't be queried directly; a keyed HMAC of the normalized
# value gives an indexable, non-reversible lookup column instead.
LOOKUP_INDEX_KEY = os.environ.get("LOOKUP_INDEX_KEY", "dev-only-lookup-index-key-override-in-.env").encode()

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "accounts.authentication.SessionTokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [],
    "UNAUTHENTICATED_USER": None,
}
