export type Role = "SUPER_ADMIN" | "PROJECT_MANAGER" | "DEVOPS_ENGINEER" | "BACKEND_DEVELOPER";

export type PlatformType = "DOMAIN" | "HOSTING" | "EMAIL" | "OTHER";
export type Environment = "PRODUCTION" | "STAGING" | "DEVELOPMENT";
export type ApprovalStatus = "PENDING" | "APPROVED" | "REJECTED";
export type NoteKind = "note" | "issue";
export type IssueStatus = "open" | "resolved";

export interface Profile {
  id: number;
  username: string;
  email: string;
  contact: string;
  role: Role;
}

export interface ProjectSummary {
  id: number;
  name: string;
  manager: number | null;
  created_at: string;
}

export interface ProjectMember {
  user_id: number;
  role: Role;
  granted_at: string;
}

export interface ProjectDetail extends ProjectSummary {
  members: ProjectMember[];
  can_manage: boolean;
}

export interface RecordNote {
  id: string;
  author_id: number;
  author_role: Role;
  kind: NoteKind;
  text: string;
  at: string;
  status: IssueStatus | null;
  resolved_by: number | null;
  resolved_at: string | null;
}

export interface CredentialFields {
  platform_type: PlatformType;
  provider_name: string;
  login_url: string;
  username: string | null;
  password: string | null;
  api_key: string | null;
  notes: RecordNote[];
}

export interface PasswordRotationStatus {
  days_since_rotation: number | null;
  tone: "success" | "warning" | "danger";
}

export interface RecordSummary {
  id: number;
  platform_type: PlatformType;
  environment: Environment;
  expires_on: string | null;
  approval_status: ApprovalStatus;
  fields: CredentialFields | null;
  error: string | null;
  password_rotation: PasswordRotationStatus;
  created_by: number;
  created_at: string;
  updated_at: string;
}

export type AccessLogAction = "REVEAL" | "COPY";

export interface AccessLogEntry {
  id: number;
  user_id: number | null;
  field_name: string;
  action: AccessLogAction;
  accessed_at: string;
}

export interface ChangeRequestSummary {
  id: number;
  record_id: number;
  status: ApprovalStatus;
  proposed: Partial<CredentialFields>;
  submitted_by: number;
  reviewed_by: number | null;
  reviewed_at: string | null;
  created_at: string;
}

export type FeedEventType =
  | "PROJECT_CREATED" | "MEMBER_ADDED" | "MEMBER_REVOKED"
  | "RECORD_REQUESTED" | "RECORD_APPROVED" | "RECORD_REJECTED" | "RECORD_EDITED"
  | "CHANGE_REQUESTED" | "CHANGE_APPROVED" | "CHANGE_REJECTED"
  | "ISSUE_REPORTED" | "ISSUE_RESOLVED" | "NOTE_ADDED" | "KEY_ROTATED";

export interface FeedEvent {
  id: number;
  event_type: FeedEventType;
  message: string;
  actor_id: number | null;
  record_id: number | null;
  created_at: string;
}

export interface AdminUser {
  id: number;
  username: string;
  email: string;
  contact: string;
  role: Role;
  is_active: boolean;
  totp_confirmed: boolean;
  created_at: string;
}

export interface ProjectManagerOption {
  id: number;
  username: string;
}

export interface SessionInfo {
  id: number;
  device_label: string;
  created_at: string;
  expires_at: string;
  is_current: boolean;
}

export interface TaskSummary {
  pending_approvals: number;
  open_issues: number;
  my_pending_submissions: number;
  expiring_soon: number;
  passwords_overdue_rotation: number;
}

export type TaskDetailKind = "record" | "change_request" | "issue" | "expiring" | "overdue_password";

export interface TaskDetailItem {
  kind: TaskDetailKind;
  project_id: number;
  project_name: string;
  record_id: number;
  change_request_id?: number;
  note_id?: string;
  provider_name: string | null;
  platform_type: PlatformType;
  detail: string;
  created_at?: string;
  expires_on?: string;
  days_since_rotation?: number | null;
}
