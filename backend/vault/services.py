"""Project/CredentialRecord crypto operations, plus the access-grant,
approval, change-request, rotation, revocation, and feed-logging workflow.
"""

import json
import uuid
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from accounts import keys as user_keys
from accounts.models import Role
from crypto_core import ecc, rsa
from crypto_core.sha256 import sha256
from grimoire import master_key

from . import hmac_utils
from .models import (AccessAction, AccessGrant, ApprovalStatus, ChangeRequest,
                      CredentialRecord, Environment, FeedEvent, FeedEventType,
                      KeyRotationLog, Project, RecordAccessLog)

_SECRET_FIELDS = ("username", "password", "api_key")
_EDITABLE_FIELDS = ("provider_name", "login_url", "username", "password", "api_key")


class AccessDenied(Exception):
    pass


# --- key helpers -------------------------------------------------------

def _project_rsa_public(project: Project) -> rsa.RSAPublicKey:
    return rsa.RSAPublicKey(n=int(project.rsa_pub_n), e=project.rsa_pub_e)


def _project_rsa_private(project: Project) -> rsa.RSAPrivateKey:
    d = int.from_bytes(master_key.unwrap(bytes(project.rsa_priv_wrapped)), "big")
    return rsa.RSAPrivateKey(n=int(project.rsa_pub_n), d=d)


def _encrypt_payload(payload: dict, pub: rsa.RSAPublicKey) -> tuple:
    blob = rsa.serialize_blocks(rsa.encrypt_chunked(json.dumps(payload).encode("utf-8"), pub))
    return blob, hmac_utils.compute(blob)


def _decrypt_payload(blob: bytes, hmac_tag: str, priv: rsa.RSAPrivateKey) -> dict:
    hmac_utils.verify(blob, hmac_tag)
    plaintext = rsa.decrypt_chunked(rsa.deserialize_blocks(blob), priv)
    return json.loads(plaintext.decode("utf-8"))


# --- permissions ---------------------------------------------------------

def has_project_access(user, project: Project) -> bool:
    if user.role == Role.SUPER_ADMIN:
        return True
    if project.manager_id == user.pk:
        return True
    return AccessGrant.objects.filter(project=project, user=user, revoked_at__isnull=True).exists()


def accessible_projects(user):
    if user.role == Role.SUPER_ADMIN:
        return Project.objects.all()
    grant_project_ids = AccessGrant.objects.filter(
        user=user, revoked_at__isnull=True
    ).values_list("project_id", flat=True)
    return Project.objects.filter(Q(manager=user) | Q(id__in=list(grant_project_ids)))


def managed_projects(user):
    if user.role == Role.SUPER_ADMIN:
        return Project.objects.all()
    if user.role == Role.PROJECT_MANAGER:
        return Project.objects.filter(manager=user)
    return Project.objects.none()


def is_project_manager_of(user, project: Project) -> bool:
    return user.role == Role.PROJECT_MANAGER and project.manager_id == user.pk


def can_manage_project(user, project: Project) -> bool:
    """Approve/reject records and change requests, grant/revoke access, rotate keys."""
    return user.role == Role.SUPER_ADMIN or is_project_manager_of(user, project)


def can_create_record(user, project: Project) -> bool:
    return has_project_access(user, project) and user.role in (
        Role.SUPER_ADMIN, Role.PROJECT_MANAGER, Role.DEVOPS_ENGINEER,
    )


def mask_fields_for_role(fields: dict, role: str) -> dict:
    """Hide secret field values from Backend Developers."""
    if role != Role.BACKEND_DEVELOPER:
        return fields
    masked = dict(fields)
    for key in _SECRET_FIELDS:
        if key in masked:
            masked[key] = None
    return masked


# --- feed ------------------------------------------------------------

def log_event(project: Project, actor, event_type: str, message: str, record=None) -> None:
    blob, tag = _encrypt_payload({"text": message}, _project_rsa_public(project))
    FeedEvent.objects.create(
        project=project, record=record, actor=actor, event_type=event_type,
        message_enc=blob, message_hmac=tag,
    )


def list_feed(project: Project) -> list:
    priv = _project_rsa_private(project)
    events = []
    for event in project.feed_events.select_related("actor").all():
        try:
            text = _decrypt_payload(bytes(event.message_enc), event.message_hmac, priv)["text"]
        except (hmac_utils.IntegrityError, rsa.OAEPError):
            text = "<integrity check failed>"
        events.append({
            "id": event.pk,
            "event_type": event.event_type,
            "message": text,
            "actor_id": event.actor_id,
            "record_id": event.record_id,
            "created_at": event.created_at,
        })
    return events


# --- projects ------------------------------------------------------------

def create_project(name: str, manager, creator) -> Project:
    rsa_pub, rsa_priv = rsa.generate_keypair(2048)
    name_enc, name_hmac = _encrypt_payload({"name": name}, rsa_pub)

    project = Project.objects.create(
        name_enc=name_enc,
        name_hmac=name_hmac,
        rsa_pub_n=str(rsa_pub.n),
        rsa_pub_e=rsa_pub.e,
        rsa_priv_wrapped=master_key.wrap(rsa_priv.d.to_bytes((rsa_priv.d.bit_length() + 7) // 8 or 1, "big")),
        manager=manager,
        created_by=creator,
    )

    _issue_grant(project, manager, granted_by=creator)
    log_event(project, creator, FeedEventType.PROJECT_CREATED, f"created the project and assigned {manager.pk} as Project Manager")
    return project


def decrypt_project_name(project: Project) -> str:
    return _decrypt_payload(bytes(project.name_enc), project.name_hmac, _project_rsa_private(project))["name"]


# --- credential records ---------------------------------------------------

def _default_fields(platform_type: str, provider_name: str, login_url: str, username: str,
                     password: str, api_key: str) -> dict:
    return {
        "platform_type": platform_type,
        "provider_name": provider_name,
        "login_url": login_url,
        "username": username,
        "password": password,
        "api_key": api_key,
        "notes": [],
    }


def create_record(project: Project, creator, platform_type: str, provider_name: str,
                   login_url: str = "", username: str = "", password: str = "", api_key: str = "",
                   environment: str = Environment.PRODUCTION, expires_on=None) -> CredentialRecord:
    fields = _default_fields(platform_type, provider_name, login_url, username, password, api_key)
    fields_enc, hmac_tag = _encrypt_payload(fields, _project_rsa_public(project))

    auto_approved = creator.role in (Role.SUPER_ADMIN, Role.PROJECT_MANAGER)
    record = CredentialRecord.objects.create(
        project=project,
        platform_type=platform_type,
        environment=environment,
        expires_on=expires_on,
        password_last_rotated=timezone.now() if password else None,
        fields_enc=fields_enc,
        hmac_tag=hmac_tag,
        approval_status=ApprovalStatus.APPROVED if auto_approved else ApprovalStatus.PENDING,
        created_by=creator,
        reviewed_by=creator if auto_approved else None,
        reviewed_at=timezone.now() if auto_approved else None,
    )

    if auto_approved:
        log_event(project, creator, FeedEventType.RECORD_APPROVED,
                   f"added a {platform_type.title()} credential ({provider_name})", record=record)
    else:
        log_event(project, creator, FeedEventType.RECORD_REQUESTED,
                   f"requested to add a {platform_type.title()} credential ({provider_name})", record=record)
    return record


def decrypt_record(record: CredentialRecord) -> dict:
    return _decrypt_payload(bytes(record.fields_enc), record.hmac_tag, _project_rsa_private(record.project))


def _save_record_fields(record: CredentialRecord, fields: dict, password_changed: bool = False) -> None:
    fields_enc, hmac_tag = _encrypt_payload(fields, _project_rsa_public(record.project))
    record.fields_enc = fields_enc
    record.hmac_tag = hmac_tag
    record.updated_at = timezone.now()
    update_fields = ["fields_enc", "hmac_tag", "updated_at"]
    if password_changed:
        record.password_last_rotated = timezone.now()
        update_fields.append("password_last_rotated")
    record.save(update_fields=update_fields)


def password_rotation_status(record: CredentialRecord) -> dict:
    """Age-based password rotation hygiene signal."""
    if record.password_last_rotated is None:
        return {"days_since_rotation": None, "tone": "warning"}
    days = (timezone.now() - record.password_last_rotated).days
    if days > 90:
        tone = "danger"
    elif days > 60:
        tone = "warning"
    else:
        tone = "success"
    return {"days_since_rotation": days, "tone": tone}


def approve_record(record: CredentialRecord, reviewer) -> None:
    if not can_manage_project(reviewer, record.project):
        raise AccessDenied("only the project's manager or a Super Admin can approve records")
    record.approval_status = ApprovalStatus.APPROVED
    record.reviewed_by = reviewer
    record.reviewed_at = timezone.now()
    record.save(update_fields=["approval_status", "reviewed_by", "reviewed_at"])
    fields = decrypt_record(record)
    log_event(record.project, reviewer, FeedEventType.RECORD_APPROVED,
               f"approved the {fields['platform_type'].title()} credential ({fields['provider_name']})", record=record)


def reject_record(record: CredentialRecord, reviewer) -> None:
    if not can_manage_project(reviewer, record.project):
        raise AccessDenied("only the project's manager or a Super Admin can reject records")
    record.approval_status = ApprovalStatus.REJECTED
    record.reviewed_by = reviewer
    record.reviewed_at = timezone.now()
    record.save(update_fields=["approval_status", "reviewed_by", "reviewed_at"])
    fields = decrypt_record(record)
    log_event(record.project, reviewer, FeedEventType.RECORD_REJECTED,
               f"rejected the {fields['platform_type'].title()} credential ({fields['provider_name']})", record=record)


def update_record_metadata(record: CredentialRecord, requester, environment: str = None,
                            expires_on=None, update_expiry: bool = False) -> None:
    """Update non-secret metadata directly, no approval needed. `update_expiry`
    distinguishes "leave expiry alone" from "clear it" (expires_on=None)."""
    if requester.role not in (Role.SUPER_ADMIN, Role.PROJECT_MANAGER, Role.DEVOPS_ENGINEER):
        raise AccessDenied("only DevOps, the Project Manager, or a Super Admin can update this")
    if not has_project_access(requester, record.project):
        raise AccessDenied("forbidden")

    update_fields = []
    if environment is not None:
        record.environment = environment
        update_fields.append("environment")
    if update_expiry:
        record.expires_on = expires_on
        update_fields.append("expires_on")
    if update_fields:
        record.save(update_fields=update_fields)


def update_record_pending(record: CredentialRecord, requester, **edits) -> None:
    """Direct edit, only while the record hasn't been approved yet."""
    if record.approval_status != ApprovalStatus.PENDING:
        raise AccessDenied("record is no longer pending; submit a change request instead")
    if requester.pk != record.created_by_id and not can_manage_project(requester, record.project):
        raise AccessDenied("only the requester or the project's manager can edit a pending record")
    fields = decrypt_record(record)
    old_password = fields.get("password")
    fields.update({k: v for k, v in edits.items() if k in _EDITABLE_FIELDS})
    password_changed = "password" in edits and edits["password"] != old_password
    _save_record_fields(record, fields, password_changed=password_changed)


# --- change requests -------------------------------------------------------

def submit_change_request(record: CredentialRecord, submitter, **edits) -> ChangeRequest:
    if record.approval_status != ApprovalStatus.APPROVED:
        raise AccessDenied("only an approved record can receive a change request")
    if not has_project_access(submitter, record.project) or submitter.role not in (
        Role.SUPER_ADMIN, Role.PROJECT_MANAGER, Role.DEVOPS_ENGINEER,
    ):
        raise AccessDenied("you cannot propose changes to this record")

    current = decrypt_record(record)
    proposed = {k: current.get(k, "") for k in _EDITABLE_FIELDS}
    proposed.update({k: v for k, v in edits.items() if k in _EDITABLE_FIELDS})
    blob, tag = _encrypt_payload(proposed, _project_rsa_public(record.project))

    auto_approved = can_manage_project(submitter, record.project)
    change_request = ChangeRequest.objects.create(
        record=record, proposed_fields_enc=blob, proposed_hmac=tag,
        status=ApprovalStatus.APPROVED if auto_approved else ApprovalStatus.PENDING,
        submitted_by=submitter,
        reviewed_by=submitter if auto_approved else None,
        reviewed_at=timezone.now() if auto_approved else None,
    )

    if auto_approved:
        _apply_change_request(change_request)
        log_event(record.project, submitter, FeedEventType.CHANGE_APPROVED,
                   f"edited the {current['provider_name']} credential", record=record)
    else:
        log_event(record.project, submitter, FeedEventType.CHANGE_REQUESTED,
                   f"requested a change to the {current['provider_name']} credential", record=record)
    return change_request


def decrypt_change_request_proposal(change_request: ChangeRequest) -> dict:
    priv = _project_rsa_private(change_request.record.project)
    return _decrypt_payload(bytes(change_request.proposed_fields_enc), change_request.proposed_hmac, priv)


def _apply_change_request(change_request: ChangeRequest) -> None:
    priv = _project_rsa_private(change_request.record.project)
    proposed = _decrypt_payload(bytes(change_request.proposed_fields_enc), change_request.proposed_hmac, priv)
    current = decrypt_record(change_request.record)
    old_password = current.get("password")
    current.update({k: proposed[k] for k in _EDITABLE_FIELDS})
    password_changed = proposed.get("password") != old_password
    _save_record_fields(change_request.record, current, password_changed=password_changed)


def approve_change_request(change_request: ChangeRequest, reviewer) -> None:
    if not can_manage_project(reviewer, change_request.record.project):
        raise AccessDenied("only the project's manager or a Super Admin can approve a change request")
    if change_request.status != ApprovalStatus.PENDING:
        raise AccessDenied("this change request has already been reviewed")

    _apply_change_request(change_request)
    change_request.status = ApprovalStatus.APPROVED
    change_request.reviewed_by = reviewer
    change_request.reviewed_at = timezone.now()
    change_request.save(update_fields=["status", "reviewed_by", "reviewed_at"])

    fields = decrypt_record(change_request.record)
    log_event(change_request.record.project, reviewer, FeedEventType.CHANGE_APPROVED,
               f"approved a change to the {fields['provider_name']} credential", record=change_request.record)


def reject_change_request(change_request: ChangeRequest, reviewer) -> None:
    if not can_manage_project(reviewer, change_request.record.project):
        raise AccessDenied("only the project's manager or a Super Admin can reject a change request")
    if change_request.status != ApprovalStatus.PENDING:
        raise AccessDenied("this change request has already been reviewed")

    change_request.status = ApprovalStatus.REJECTED
    change_request.reviewed_by = reviewer
    change_request.reviewed_at = timezone.now()
    change_request.save(update_fields=["status", "reviewed_by", "reviewed_at"])

    fields = decrypt_record(change_request.record)
    log_event(change_request.record.project, reviewer, FeedEventType.CHANGE_REJECTED,
               f"rejected a change to the {fields['provider_name']} credential", record=change_request.record)


# --- notes / issues --------------------------------------------------------

def add_note(record: CredentialRecord, author, text: str, kind: str = "note") -> dict:
    if kind not in ("note", "issue"):
        raise ValueError("kind must be 'note' or 'issue'")

    fields = decrypt_record(record)
    note = {
        "id": uuid.uuid4().hex,
        "author_id": author.pk,
        "author_role": author.role,
        "kind": kind,
        "text": text,
        "at": timezone.now().isoformat(),
        "status": "open" if kind == "issue" else None,
        "resolved_by": None,
        "resolved_at": None,
    }
    fields.setdefault("notes", []).append(note)
    _save_record_fields(record, fields)

    event_type = FeedEventType.ISSUE_REPORTED if kind == "issue" else FeedEventType.NOTE_ADDED
    verb = "reported an issue on" if kind == "issue" else "left a note on"
    log_event(record.project, author, event_type, f"{verb} the {fields['provider_name']} credential: {text}", record=record)
    return note


def resolve_issue(record: CredentialRecord, note_id: str, resolver) -> dict:
    if resolver.role not in (Role.SUPER_ADMIN, Role.PROJECT_MANAGER, Role.DEVOPS_ENGINEER):
        raise AccessDenied("only DevOps, the Project Manager, or a Super Admin can resolve an issue")

    fields = decrypt_record(record)
    for note in fields.get("notes", []):
        if note["id"] == note_id and note["kind"] == "issue":
            if note["status"] == "resolved":
                raise AccessDenied("issue is already resolved")
            note["status"] = "resolved"
            note["resolved_by"] = resolver.pk
            note["resolved_at"] = timezone.now().isoformat()
            _save_record_fields(record, fields)
            log_event(record.project, resolver, FeedEventType.ISSUE_RESOLVED,
                       f"resolved an issue on the {fields['provider_name']} credential", record=record)
            return note
    raise AccessDenied("no such open issue on this record")


# --- access audit log -------------------------------------------------------

_LOGGABLE_FIELDS = ("username", "password", "api_key")


def log_record_access(record: CredentialRecord, user, field_name: str, action: str) -> None:
    """Log an explicit reveal/copy of a secret field value."""
    if field_name not in _LOGGABLE_FIELDS or action not in AccessAction.values:
        raise ValueError("invalid field_name or action")
    RecordAccessLog.objects.create(record=record, user=user, field_name=field_name, action=action)


def list_access_log(record: CredentialRecord) -> list:
    return [
        {
            "id": entry.pk,
            "user_id": entry.user_id,
            "field_name": entry.field_name,
            "action": entry.action,
            "accessed_at": entry.accessed_at,
        }
        for entry in record.access_logs.select_related("user").all()[:100]
    ]


# --- access grants / rotation / revocation ---------------------------------

def _issue_grant(project: Project, target_user, granted_by) -> AccessGrant:
    rsa_priv = _project_rsa_private(project)
    payload = rsa_priv.n.to_bytes(256, "big") + rsa_priv.d.to_bytes((rsa_priv.d.bit_length() + 7) // 8 or 1, "big")
    ecc_pub = user_keys.get_ecc_public(target_user)
    wrapped = ecc.serialize_blocks(ecc.encrypt_chunked(payload, ecc_pub))

    existing = AccessGrant.objects.filter(project=project, user=target_user, revoked_at__isnull=True).first()
    if existing is not None:
        existing.wrapped_project_privkey = wrapped
        existing.granted_by = granted_by
        existing.save(update_fields=["wrapped_project_privkey", "granted_by"])
        return existing

    return AccessGrant.objects.create(
        project=project, user=target_user, wrapped_project_privkey=wrapped, granted_by=granted_by,
    )


def grant_access(project: Project, target_user, granted_by) -> AccessGrant:
    if not can_manage_project(granted_by, project):
        raise AccessDenied("only the project's manager or a Super Admin can add members")
    if target_user.role not in (Role.DEVOPS_ENGINEER, Role.BACKEND_DEVELOPER):
        raise AccessDenied("only DevOps Engineers or Backend Developers can be added to a project this way")

    grant = _issue_grant(project, target_user, granted_by)
    log_event(project, granted_by, FeedEventType.MEMBER_ADDED,
               f"added user {target_user.pk} ({target_user.role}) to the project")
    return grant


def unwrap_grant(grant: AccessGrant) -> tuple:
    """Decrypt an AccessGrant using the grantee's ECC private key. Returns (n, d)."""
    ecc_priv = user_keys.get_ecc_private(grant.user)
    blocks = ecc.deserialize_blocks(bytes(grant.wrapped_project_privkey))
    payload = ecc.decrypt_chunked(blocks, ecc_priv)
    n = int.from_bytes(payload[:256], "big")
    d = int.from_bytes(payload[256:], "big")
    return n, d


def _rotate(project: Project, reason: str, rotated_by, exclude_user=None) -> None:
    old_fingerprint = sha256(str(project.rsa_pub_n).encode()).hex()

    new_pub, new_priv = rsa.generate_keypair(2048)
    old_priv = _project_rsa_private(project)

    name_plain = _decrypt_payload(bytes(project.name_enc), project.name_hmac, old_priv)
    new_name_enc, new_name_hmac = _encrypt_payload(name_plain, new_pub)

    records = list(project.records.all())
    decrypted_payloads = [_decrypt_payload(bytes(r.fields_enc), r.hmac_tag, old_priv) for r in records]

    # Change requests are encrypted under the same project key and must be re-wrapped too.
    change_requests = list(ChangeRequest.objects.filter(record__project=project))
    decrypted_cr_payloads = [
        _decrypt_payload(bytes(cr.proposed_fields_enc), cr.proposed_hmac, old_priv) for cr in change_requests
    ]

    # Feed messages are encrypted under the same key too.
    feed_events = list(project.feed_events.all())
    decrypted_feed_payloads = [
        _decrypt_payload(bytes(e.message_enc), e.message_hmac, old_priv) for e in feed_events
    ]

    project.name_enc = new_name_enc
    project.name_hmac = new_name_hmac
    project.rsa_pub_n = str(new_pub.n)
    project.rsa_pub_e = new_pub.e
    project.rsa_priv_wrapped = master_key.wrap(new_priv.d.to_bytes((new_priv.d.bit_length() + 7) // 8 or 1, "big"))
    project.save(update_fields=["name_enc", "name_hmac", "rsa_pub_n", "rsa_pub_e", "rsa_priv_wrapped"])

    for record, payload in zip(records, decrypted_payloads):
        new_fields_enc, new_hmac_tag = _encrypt_payload(payload, new_pub)
        record.fields_enc = new_fields_enc
        record.hmac_tag = new_hmac_tag
        record.updated_at = timezone.now()
        record.save(update_fields=["fields_enc", "hmac_tag", "updated_at"])

    for change_request, payload in zip(change_requests, decrypted_cr_payloads):
        new_proposed_enc, new_proposed_hmac = _encrypt_payload(payload, new_pub)
        change_request.proposed_fields_enc = new_proposed_enc
        change_request.proposed_hmac = new_proposed_hmac
        change_request.save(update_fields=["proposed_fields_enc", "proposed_hmac"])

    for event, payload in zip(feed_events, decrypted_feed_payloads):
        new_message_enc, new_message_hmac = _encrypt_payload(payload, new_pub)
        event.message_enc = new_message_enc
        event.message_hmac = new_message_hmac
        event.save(update_fields=["message_enc", "message_hmac"])

    for grant in AccessGrant.objects.filter(project=project, revoked_at__isnull=True):
        if exclude_user is not None and grant.user_id == exclude_user.pk:
            continue
        _issue_grant(project, grant.user, granted_by=rotated_by)

    KeyRotationLog.objects.create(
        scope=KeyRotationLog.Scope.PROJECT,
        scope_id=project.pk,
        reason=reason,
        previous_key_fingerprint=old_fingerprint,
        rotated_by=rotated_by,
    )
    log_event(project, rotated_by, FeedEventType.KEY_ROTATED, "rotated the project's encryption key")


def rotate_project_key(project: Project, rotated_by, reason: str = KeyRotationLog.Reason.MANUAL) -> None:
    if not can_manage_project(rotated_by, project):
        raise AccessDenied("only the project's manager or a Super Admin can rotate the project key")
    _rotate(project, reason, rotated_by)


def revoke_access(project: Project, target_user, revoked_by) -> None:
    if not can_manage_project(revoked_by, project):
        raise AccessDenied("only the project's manager or a Super Admin can revoke access")

    grant = AccessGrant.objects.filter(project=project, user=target_user, revoked_at__isnull=True).first()
    if grant is None:
        return
    grant.revoked_at = timezone.now()
    grant.save(update_fields=["revoked_at"])

    log_event(project, revoked_by, FeedEventType.MEMBER_REVOKED, f"revoked access for user {target_user.pk}")
    _rotate(project, KeyRotationLog.Reason.REVOCATION, revoked_by, exclude_user=target_user)


# --- dashboard summary ---------------------------------------------------

def task_summary(user) -> dict:
    """Role-aware dashboard summary: pending approvals, open issues, own submissions."""
    managed = managed_projects(user)
    pending_records = CredentialRecord.objects.filter(
        project__in=managed, approval_status=ApprovalStatus.PENDING
    ).count()
    pending_change_requests = ChangeRequest.objects.filter(
        record__project__in=managed, status=ApprovalStatus.PENDING
    ).count()

    open_issues = 0
    for record in CredentialRecord.objects.filter(project__in=accessible_projects(user)):
        try:
            fields = decrypt_record(record)
        except (hmac_utils.IntegrityError, rsa.OAEPError):
            continue
        open_issues += sum(1 for note in fields.get("notes", []) if note["kind"] == "issue" and note["status"] == "open")

    my_pending_submissions = (
        CredentialRecord.objects.filter(created_by=user, approval_status=ApprovalStatus.PENDING).count()
        + ChangeRequest.objects.filter(submitted_by=user, status=ApprovalStatus.PENDING).count()
    )

    expiring_soon = CredentialRecord.objects.filter(
        project__in=accessible_projects(user),
        approval_status=ApprovalStatus.APPROVED,
        expires_on__isnull=False,
        expires_on__lte=timezone.now().date() + timedelta(days=30),
    ).count()

    rotation_cutoff = timezone.now() - timedelta(days=90)
    passwords_overdue_rotation = CredentialRecord.objects.filter(
        project__in=accessible_projects(user),
        approval_status=ApprovalStatus.APPROVED,
    ).filter(
        Q(password_last_rotated__isnull=True) | Q(password_last_rotated__lt=rotation_cutoff)
    ).count()

    return {
        "pending_approvals": pending_records + pending_change_requests,
        "open_issues": open_issues,
        "my_pending_submissions": my_pending_submissions,
        "expiring_soon": expiring_soon,
        "passwords_overdue_rotation": passwords_overdue_rotation,
    }

