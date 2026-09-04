from django.urls import path

from . import views

urlpatterns = [
    path("register", views.RegisterView.as_view()),
    path("totp/confirm", views.ConfirmTotpView.as_view()),
    path("login/step1", views.LoginStep1View.as_view()),
    path("login/step2", views.LoginStep2View.as_view()),
    path("logout", views.LogoutView.as_view()),
    path("profile", views.ProfileView.as_view()),
    path("sessions", views.SessionListView.as_view()),
    path("sessions/<int:session_id>/revoke", views.SessionRevokeView.as_view()),
    path("users/lookup", views.UserLookupView.as_view()),
    path("admin/users", views.AdminListUsersView.as_view()),
    path("admin/users/create", views.AdminCreateUserView.as_view()),
]
