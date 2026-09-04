"""No django.contrib.admin. See settings.py and accounts/views.py's
AdminCreateUserView/AdminListUsersView for the from-scratch replacement."""

from django.urls import include, path

urlpatterns = [
    path("api/auth/", include("accounts.urls")),
    path("api/vault/", include("vault.urls")),
]
