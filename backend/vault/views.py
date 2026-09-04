from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts import profile as profile_module
from accounts.authentication import SessionTokenAuthentication
from accounts.models import Role, User
from accounts.permissions import IsAuthenticated, IsSuperAdmin
from crypto_core import rsa

from . import hmac_utils, services
from .models import (AccessGrant, ChangeRequest, CredentialRecord, Environment,
                      KeyRotationLog, PlatformType, Project)


def _serialize_record(record: CredentialRecord, viewer_role: str) -> dict:
    try:
        fields = services.decrypt_record(record)
        fields = services.mask_fields_for_role(fields, viewer_role)
        error = None
    except (hmac_utils.IntegrityError, rsa.OAEPError):
        fields, error = None, "integrity check failed"
    return {
        "id": record.pk,
        "platform_type": record.platform_type,
        "environment": record.environment,
        "expires_on": record.expires_on,
        "approval_status": record.approval_status,
        "fields": fields,
        "error": error,
        "password_rotation": services.password_rotation_status(record),
        "created_by": record.created_by_id,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


class ProjectListCreateView(APIView):
    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        projects = services.accessible_projects(request.user).order_by("-created_at")
        results = []
        for project in projects:
            try:
                name = services.decrypt_project_name(project)
            except (hmac_utils.IntegrityError, rsa.OAEPError):
                name = "<integrity check failed>"
            results.append({
                "id": project.pk, "name": name, "manager": project.manager_id, "created_at": project.created_at,
            })
        return Response(results)

    def post(self, request):
        if request.user.role != Role.SUPER_ADMIN:
            return Response({"error": "only a Super Admin can create a project"}, status=403)

        name = (request.data.get("name") or "").strip()
        manager_id = request.data.get("manager_id")
        if not name or not manager_id:
            return Response({"error": "name and manager_id are required"}, status=400)

        manager = get_object_or_404(User, pk=manager_id)
        if manager.role != Role.PROJECT_MANAGER:
            return Response({"error": "manager_id must belong to a Project Manager"}, status=400)

        project = services.create_project(name, manager, request.user)
        return Response({"id": project.pk, "name": name, "manager": manager.pk}, status=201)


class ProjectDetailView(APIView):
    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        if not services.has_project_access(request.user, project):
            return Response({"error": "forbidden"}, status=403)

        try:
            name = services.decrypt_project_name(project)
        except (hmac_utils.IntegrityError, rsa.OAEPError):
            return Response({"error": "project integrity check failed"}, status=500)

        grants = AccessGrant.objects.filter(project=project, revoked_at__isnull=True).select_related("user")
        members = [{"user_id": g.user_id, "role": g.user.role, "granted_at": g.granted_at} for g in grants]
        return Response({
            "id": project.pk, "name": name, "manager": project.manager_id,
            "created_at": project.created_at, "members": members,
            "can_manage": services.can_manage_project(request.user, project),
        })


class RecordListCreateView(APIView):
    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        if not services.has_project_access(request.user, project):
            return Response({"error": "forbidden"}, status=403)

        records = project.records.all().order_by("-created_at")
        platform_type = request.query_params.get("platform_type")
        if platform_type:
            records = records.filter(platform_type=platform_type)
        environment = request.query_params.get("environment")
        if environment:
            records = records.filter(environment=environment)
        approval_status = request.query_params.get("approval_status")
        if approval_status:
            records = records.filter(approval_status=approval_status)

        return Response([_serialize_record(r, request.user.role) for r in records])

    def post(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        if not services.can_create_record(request.user, project):
            return Response({"error": "you cannot add credentials to this project"}, status=403)

        platform_type = request.data.get("platform_type")
        provider_name = (request.data.get("provider_name") or "").strip()
        if platform_type not in PlatformType.values or not provider_name:
            return Response({"error": f"platform_type must be one of {PlatformType.values}, provider_name is required"}, status=400)

        environment = request.data.get("environment") or Environment.PRODUCTION
        if environment not in Environment.values:
            return Response({"error": f"environment must be one of {Environment.values}"}, status=400)

        record = services.create_record(
            project, request.user, platform_type, provider_name,
            login_url=request.data.get("login_url", ""),
            username=request.data.get("username", ""),
            password=request.data.get("password", ""),
            api_key=request.data.get("api_key", ""),
            environment=environment,
            expires_on=request.data.get("expires_on") or None,
        )
        return Response(_serialize_record(record, request.user.role), status=201)


class RecordDetailView(APIView):
    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id, record_id):
        record = get_object_or_404(CredentialRecord, pk=record_id, project_id=project_id)
        if not services.has_project_access(request.user, record.project):
            return Response({"error": "forbidden"}, status=403)
        return Response(_serialize_record(record, request.user.role))

    def put(self, request, project_id, record_id):
        record = get_object_or_404(CredentialRecord, pk=record_id, project_id=project_id)
        if not services.has_project_access(request.user, record.project):
            return Response({"error": "forbidden"}, status=403)

        edits = {k: request.data[k] for k in ("provider_name", "login_url", "username", "password", "api_key") if k in request.data}
        try:
            services.update_record_pending(record, request.user, **edits)
        except services.AccessDenied as exc:
            return Response({"error": str(exc)}, status=403)
        return Response(_serialize_record(record, request.user.role))


class RecordMetadataView(APIView):
    """Update non-secret metadata (environment, expiry) without approval."""

    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id, record_id):
        record = get_object_or_404(CredentialRecord, pk=record_id, project_id=project_id)
        environment = request.data.get("environment")
        if environment is not None and environment not in Environment.values:
            return Response({"error": f"environment must be one of {Environment.values}"}, status=400)

        has_expiry = "expires_on" in request.data
        try:
            services.update_record_metadata(
                record, request.user, environment=environment,
                expires_on=request.data.get("expires_on") or None, update_expiry=has_expiry,
            )
        except services.AccessDenied as exc:
            return Response({"error": str(exc)}, status=403)
        return Response(_serialize_record(record, request.user.role))


class RecordApproveView(APIView):
    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id, record_id):
        record = get_object_or_404(CredentialRecord, pk=record_id, project_id=project_id)
        try:
            services.approve_record(record, request.user)
        except services.AccessDenied as exc:
            return Response({"error": str(exc)}, status=403)
        return Response(_serialize_record(record, request.user.role))


class RecordRejectView(APIView):
    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id, record_id):
        record = get_object_or_404(CredentialRecord, pk=record_id, project_id=project_id)
        try:
            services.reject_record(record, request.user)
        except services.AccessDenied as exc:
            return Response({"error": str(exc)}, status=403)
        return Response(_serialize_record(record, request.user.role))


def _serialize_change_request(cr: ChangeRequest, viewer_role: str) -> dict:
    try:
        proposed = services.mask_fields_for_role(services.decrypt_change_request_proposal(cr), viewer_role)
        error = None
    except (hmac_utils.IntegrityError, rsa.OAEPError):
        proposed, error = None, "integrity check failed"
    return {
        "id": cr.pk,
        "record_id": cr.record_id,
        "status": cr.status,
        "proposed": proposed,
        "error": error,
        "submitted_by": cr.submitted_by_id,
        "reviewed_by": cr.reviewed_by_id,
        "reviewed_at": cr.reviewed_at,
        "created_at": cr.created_at,
    }


class ChangeRequestListCreateView(APIView):
    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id, record_id):
        record = get_object_or_404(CredentialRecord, pk=record_id, project_id=project_id)
        if not services.has_project_access(request.user, record.project):
            return Response({"error": "forbidden"}, status=403)
        crs = record.change_requests.all().order_by("-created_at")
        return Response([_serialize_change_request(cr, request.user.role) for cr in crs])

    def post(self, request, project_id, record_id):
        record = get_object_or_404(CredentialRecord, pk=record_id, project_id=project_id)
        edits = {k: request.data[k] for k in ("provider_name", "login_url", "username", "password", "api_key") if k in request.data}
        try:
            cr = services.submit_change_request(record, request.user, **edits)
        except services.AccessDenied as exc:
            return Response({"error": str(exc)}, status=403)
        return Response(_serialize_change_request(cr, request.user.role), status=201)


class ChangeRequestApproveView(APIView):
    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id, record_id, cr_id):
        cr = get_object_or_404(ChangeRequest, pk=cr_id, record_id=record_id, record__project_id=project_id)
        try:
            services.approve_change_request(cr, request.user)
        except services.AccessDenied as exc:
            return Response({"error": str(exc)}, status=403)
        return Response(_serialize_change_request(cr, request.user.role))


class ChangeRequestRejectView(APIView):
    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id, record_id, cr_id):
        cr = get_object_or_404(ChangeRequest, pk=cr_id, record_id=record_id, record__project_id=project_id)
        try:
            services.reject_change_request(cr, request.user)
        except services.AccessDenied as exc:
            return Response({"error": str(exc)}, status=403)
        return Response(_serialize_change_request(cr, request.user.role))


class RecordNoteView(APIView):
    """Leave a note or report an issue on a credential record."""

    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id, record_id):
        record = get_object_or_404(CredentialRecord, pk=record_id, project_id=project_id)
        if not services.has_project_access(request.user, record.project):
            return Response({"error": "forbidden"}, status=403)

        text = (request.data.get("text") or "").strip()
        kind = request.data.get("kind", "note")
        if not text:
            return Response({"error": "text is required"}, status=400)

        try:
            note = services.add_note(record, request.user, text, kind=kind)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=400)
        return Response(note, status=201)


class ResolveIssueView(APIView):
    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id, record_id, note_id):
        record = get_object_or_404(CredentialRecord, pk=record_id, project_id=project_id)
        try:
            note = services.resolve_issue(record, note_id, request.user)
        except services.AccessDenied as exc:
            return Response({"error": str(exc)}, status=403)
        return Response(note)


class RecordAccessLogView(APIView):
    """POST logs a secret-field reveal/copy; GET lists that history for
    whoever manages the project."""

    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id, record_id):
        record = get_object_or_404(CredentialRecord, pk=record_id, project_id=project_id)
        if not services.can_manage_project(request.user, record.project):
            return Response({"error": "forbidden"}, status=403)
        return Response(services.list_access_log(record))

    def post(self, request, project_id, record_id):
        record = get_object_or_404(CredentialRecord, pk=record_id, project_id=project_id)
        if not services.has_project_access(request.user, record.project):
            return Response({"error": "forbidden"}, status=403)

        field_name = request.data.get("field_name")
        action = request.data.get("action")
        try:
            services.log_record_access(record, request.user, field_name, action)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=400)
        return Response({"message": "logged"}, status=201)


class FeedView(APIView):
    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        if not services.has_project_access(request.user, project):
            return Response({"error": "forbidden"}, status=403)
        return Response(services.list_feed(project))


class GrantAccessView(APIView):
    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        target = get_object_or_404(User, pk=request.data.get("user_id"))
        try:
            services.grant_access(project, target, request.user)
        except services.AccessDenied as exc:
            return Response({"error": str(exc)}, status=403)
        return Response({"message": f"access granted to user {target.pk}"})


class RevokeAccessView(APIView):
    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        target = get_object_or_404(User, pk=request.data.get("user_id"))
        try:
            services.revoke_access(project, target, request.user)
        except services.AccessDenied as exc:
            return Response({"error": str(exc)}, status=403)
        return Response({"message": f"access revoked for user {target.pk}, project key rotated"})


class RotateKeyView(APIView):
    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        try:
            services.rotate_project_key(project, request.user, reason=KeyRotationLog.Reason.MANUAL)
        except services.AccessDenied as exc:
            return Response({"error": str(exc)}, status=403)
        return Response({"message": "project key rotated"})


class ProjectManagersView(APIView):
    """List Project Manager accounts, for assigning one when creating a project."""

    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        managers = User.objects.filter(role=Role.PROJECT_MANAGER, is_active=True)
        results = []
        for manager in managers:
            try:
                fields = profile_module.decrypt_profile_fields(manager)
                username = fields["username"]
            except profile_module.ProfileIntegrityError:
                username = "<integrity check failed>"
            results.append({"id": manager.pk, "username": username})
        return Response(results)


class TaskSummaryView(APIView):
    """Powers the dashboard's "needs your attention" widget."""

    authentication_classes = [SessionTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(services.task_summary(request.user))
