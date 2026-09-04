"""RBAC permission classes. request.user is our own accounts.models.User
(or None), set by SessionTokenAuthentication."""

from rest_framework.permissions import BasePermission

from .models import Role


class IsAuthenticated(BasePermission):
    def has_permission(self, request, view):
        return request.user is not None


class IsSuperAdmin(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == Role.SUPER_ADMIN


class IsProjectManager(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == Role.PROJECT_MANAGER


class IsProjectManagerOrAbove(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role in (
            Role.SUPER_ADMIN,
            Role.PROJECT_MANAGER,
        )


class IsDevOpsEngineer(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == Role.DEVOPS_ENGINEER
