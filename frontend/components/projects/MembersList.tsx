"use client";

import { UserMinus } from "lucide-react";
import { useState } from "react";

import { api, ApiError } from "@/lib/api";
import { Badge } from "@/components/shared/Badge";
import { Button } from "@/components/shared/Button";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { ErrorMessage } from "@/components/shared/ErrorMessage";
import { useToast } from "@/lib/ToastContext";
import { ProjectMember, Role } from "@/lib/types";

const ROLE_TONE: Record<Role, "accent" | "success" | "neutral" | "warning"> = {
  SUPER_ADMIN: "accent",
  PROJECT_MANAGER: "success",
  DEVOPS_ENGINEER: "neutral",
  BACKEND_DEVELOPER: "warning",
};

interface Props {
  projectId: number;
  members: ProjectMember[];
  canManage: boolean;
  onRevoked: (userId: number) => void;
}

export function MembersList({ projectId, members, canManage, onRevoked }: Props) {
  const { toast } = useToast();
  const [error, setError] = useState<string | null>(null);
  const [revokingId, setRevokingId] = useState<number | null>(null);
  const [pendingTarget, setPendingTarget] = useState<number | null>(null);

  async function handleRevoke(userId: number) {
    setError(null);
    setRevokingId(userId);
    try {
      await api.post(`/api/vault/projects/${projectId}/revoke`, { user_id: userId });
      toast("Access revoked and the project key was rotated.");
      onRevoked(userId);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not revoke access");
    } finally {
      setRevokingId(null);
      setPendingTarget(null);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-400">Team</h3>
      {members.length === 0 ? (
        <p className="text-sm text-ink-400">No DevOps Engineers or Backend Developers added yet.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {members.map((member) => (
            <li key={member.user_id} className="flex items-center justify-between bg-sand-50 border border-sand-200 rounded-lg px-3 py-2 text-sm">
              <span className="flex items-center gap-2">
                user #{member.user_id} <Badge tone={ROLE_TONE[member.role]}>{member.role.replace("_", " ")}</Badge>
              </span>
              {canManage && (
                <Button variant="danger" onClick={() => setPendingTarget(member.user_id)}>
                  <UserMinus size={14} className="inline mr-1" /> Revoke
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}
      <ErrorMessage message={error} />

      <ConfirmDialog
        open={pendingTarget !== null}
        title="Revoke this member's access?"
        description="This rotates the project's encryption key and re-encrypts every credential. The member will lose access immediately."
        confirmLabel="Revoke access"
        loading={revokingId !== null}
        onConfirm={() => pendingTarget !== null && handleRevoke(pendingTarget)}
        onCancel={() => setPendingTarget(null)}
      />
    </div>
  );
}
