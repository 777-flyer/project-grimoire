"use client";

import { FormEvent, useState } from "react";

import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/shared/Button";
import { ErrorMessage } from "@/components/shared/ErrorMessage";
import { Input } from "@/components/shared/Input";
import { useToast } from "@/lib/ToastContext";
import { Role } from "@/lib/types";

interface LookupResponse {
  id: number;
  username: string;
  role: Role;
}

export function GrantAccessForm({ projectId, onGranted }: { projectId: number; onGranted: (userId: number, role: Role) => void }) {
  const { toast } = useToast();
  const [username, setUsername] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const user = await api.get<LookupResponse>(`/api/auth/users/lookup?username=${encodeURIComponent(username)}`);
      await api.post(`/api/vault/projects/${projectId}/grant`, { user_id: user.id });
      onGranted(user.id, user.role);
      toast(`${user.username} added to the project.`);
      setUsername("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not add member");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-2">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-400">Add a DevOps Engineer or Backend Developer</h3>
      <div className="flex items-end gap-2">
        <div className="flex-1">
          <Input label="Username" value={username} onChange={(e) => setUsername(e.target.value)} required />
        </div>
        <Button type="submit" variant="secondary" loading={loading}>Add</Button>
      </div>
      <ErrorMessage message={error} />
    </form>
  );
}
