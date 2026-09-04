"use client";

import { CheckCircle2, Clock, Globe, Mail, Server, Tag, XCircle } from "lucide-react";
import { useState } from "react";

import { api, ApiError } from "@/lib/api";
import { AccessLogPanel } from "@/components/projects/AccessLogPanel";
import { Badge } from "@/components/shared/Badge";
import { Button } from "@/components/shared/Button";
import { ChangeRequestPanel } from "@/components/projects/ChangeRequestPanel";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { ErrorMessage } from "@/components/shared/ErrorMessage";
import { ExpiryBadge } from "@/components/projects/ExpiryBadge";
import { Input } from "@/components/shared/Input";
import { MetadataEditor } from "@/components/projects/MetadataEditor";
import { NotesThread } from "@/components/projects/NotesThread";
import { PasswordRotationBadge } from "@/components/projects/PasswordRotationBadge";
import { QuickConnect } from "@/components/projects/QuickConnect";
import { SecretField } from "@/components/projects/SecretField";
import { useAuth } from "@/lib/AuthContext";
import { useToast } from "@/lib/ToastContext";
import { ApprovalStatus, Environment, RecordSummary } from "@/lib/types";

const ENVIRONMENT_TONE: Record<Environment, "accent" | "warning" | "neutral"> = {
  PRODUCTION: "accent", STAGING: "warning", DEVELOPMENT: "neutral",
};

const STATUS_TONE: Record<ApprovalStatus, "warning" | "success" | "danger"> = {
  PENDING: "warning", APPROVED: "success", REJECTED: "danger",
};

const STATUS_ICON: Record<ApprovalStatus, typeof Clock> = {
  PENDING: Clock, APPROVED: CheckCircle2, REJECTED: XCircle,
};

const PLATFORM_META: Record<string, { label: string; icon: typeof Globe }> = {
  DOMAIN: { label: "Domain", icon: Globe },
  HOSTING: { label: "Hosting", icon: Server },
  EMAIL: { label: "Email", icon: Mail },
  OTHER: { label: "Other", icon: Tag },
};

const FIELD_LABELS: Record<string, string> = {
  provider_name: "Provider",
  login_url: "Login URL",
  username: "Username",
  password: "Password",
  api_key: "API key",
};

interface Props {
  projectId: number;
  record: RecordSummary;
  canManage: boolean;
  onUpdated: (record: RecordSummary) => void;
}

export function RecordCard({ projectId, record, canManage, onUpdated }: Props) {
  const profile = useAuth();
  const { toast } = useToast();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(() => ({ ...(record.fields ?? {}) }));
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [confirmingReject, setConfirmingReject] = useState(false);

  const base = `/api/vault/projects/${projectId}/records/${record.id}`;
  const canEditWhilePending = record.approval_status === "PENDING" && (canManage || record.created_by === profile.id);
  const canPostChangeRequest = record.approval_status === "APPROVED" && profile.role !== "BACKEND_DEVELOPER";
  const canEditMetadata = profile.role !== "BACKEND_DEVELOPER";

  async function refresh() {
    try {
      const updated = await api.get<RecordSummary>(base);
      onUpdated(updated);
    } catch {
      // fire-and-forget refresh; a failure here shouldn't crash the UI
    }
  }

  async function handleReview(action: "approve" | "reject") {
    setError(null);
    setLoading(true);
    try {
      const updated = await api.post<RecordSummary>(`${base}/${action}`);
      onUpdated(updated);
      toast(action === "approve" ? "Credential approved." : "Credential rejected.", action === "approve" ? "success" : "info");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not review record");
    } finally {
      setLoading(false);
      setConfirmingReject(false);
    }
  }

  async function handleSave() {
    setError(null);
    setLoading(true);
    try {
      const updated = await api.put<RecordSummary>(base, draft);
      onUpdated(updated);
      setEditing(false);
      toast("Credential updated.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not update record");
    } finally {
      setLoading(false);
    }
  }

  if (record.error || !record.fields) {
    return (
      <div className="bg-surface border border-danger-600/30 rounded-xl p-5 text-sm text-danger-600">
        {record.error ?? "Unable to load this record."}
      </div>
    );
  }

  const platform = PLATFORM_META[record.platform_type] ?? PLATFORM_META.OTHER;
  const PlatformIcon = platform.icon;
  const StatusIcon = STATUS_ICON[record.approval_status];

  return (
    <div className="bg-surface border border-sand-200 rounded-xl p-5 flex flex-col gap-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-lg bg-accent-100 text-accent-700 flex items-center justify-center shrink-0">
            <PlatformIcon size={18} />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-1">
              <Badge tone="accent">{platform.label}</Badge>
              <Badge tone={ENVIRONMENT_TONE[record.environment]}>{record.environment.toLowerCase()}</Badge>
              <Badge tone={STATUS_TONE[record.approval_status]}>
                <StatusIcon size={11} className="inline mr-1 -mt-0.5" />
                {record.approval_status.toLowerCase()}
              </Badge>
              <ExpiryBadge expiresOn={record.expires_on} />
              {record.password_rotation.days_since_rotation !== null && (
                <PasswordRotationBadge rotation={record.password_rotation} />
              )}
              {canEditMetadata && <MetadataEditor projectId={projectId} record={record} onUpdated={onUpdated} />}
            </div>
            <h3 className="font-semibold text-ink-900">{record.fields.provider_name}</h3>
            <div className="mt-1">
              <QuickConnect
                platformType={record.platform_type}
                loginUrl={record.fields.login_url}
                username={record.fields.username}
              />
            </div>
          </div>
        </div>
        {record.approval_status === "PENDING" && canManage && (
          <div className="flex gap-2 shrink-0">
            <Button variant="secondary" loading={loading} onClick={() => handleReview("approve")}>Approve</Button>
            <Button variant="danger" onClick={() => setConfirmingReject(true)}>Reject</Button>
          </div>
        )}
      </div>

      {editing ? (
        <div className="grid sm:grid-cols-2 gap-3">
          {Object.entries(FIELD_LABELS).map(([key, label]) => (
            <Input
              key={key}
              label={label}
              type={key === "password" ? "password" : "text"}
              value={(draft[key as keyof typeof draft] as string) || ""}
              onChange={(e) => setDraft((d) => ({ ...d, [key]: e.target.value }))}
            />
          ))}
        </div>
      ) : (
        <dl className="grid sm:grid-cols-2 gap-3 text-sm">
          {Object.entries(FIELD_LABELS).map(([key, label]) => {
            const value = record.fields![key as keyof typeof record.fields] as string | null;
            const isSecret = key === "username" || key === "password" || key === "api_key";
            return (
              <div key={key}>
                <dt className="text-ink-400 text-xs uppercase tracking-wide">{label}</dt>
                <dd className="text-ink-800">
                  {isSecret
                    ? <SecretField value={value} projectId={projectId} recordId={record.id} fieldName={key} />
                    : (value || "—")}
                </dd>
              </div>
            );
          })}
        </dl>
      )}

      <ErrorMessage message={error} />

      {canEditWhilePending && (
        <div className="flex gap-2">
          {editing ? (
            <>
              <Button loading={loading} onClick={handleSave}>Save</Button>
              <Button variant="secondary" onClick={() => { setEditing(false); setDraft({ ...record.fields }); }}>
                Cancel
              </Button>
            </>
          ) : (
            <Button variant="secondary" onClick={() => setEditing(true)}>Edit while pending</Button>
          )}
        </div>
      )}

      {canPostChangeRequest && (
        <div className="border-t border-sand-200 pt-4">
          <ChangeRequestPanel projectId={projectId} recordId={record.id} canManage={canManage} onApplied={refresh} />
        </div>
      )}

      <div className="border-t border-sand-200 pt-4">
        <NotesThread projectId={projectId} recordId={record.id} notes={record.fields.notes ?? []} onChanged={refresh} />
      </div>

      {canManage && (
        <div className="border-t border-sand-200 pt-4">
          <AccessLogPanel projectId={projectId} recordId={record.id} />
        </div>
      )}

      <ConfirmDialog
        open={confirmingReject}
        title="Reject this credential?"
        description={`This marks the ${platform.label} credential (${record.fields.provider_name}) as rejected. This can't be undone from here.`}
        confirmLabel="Reject"
        loading={loading}
        onConfirm={() => handleReview("reject")}
        onCancel={() => setConfirmingReject(false)}
      />
    </div>
  );
}
