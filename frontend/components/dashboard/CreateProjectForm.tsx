"use client";

import { FormEvent, useEffect, useState } from "react";

import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/shared/Button";
import { ErrorMessage } from "@/components/shared/ErrorMessage";
import { Input } from "@/components/shared/Input";
import { Select } from "@/components/shared/Select";
import { useToast } from "@/lib/ToastContext";
import { ProjectManagerOption, ProjectSummary } from "@/lib/types";

export function CreateProjectForm({ onCreated }: { onCreated: (project: ProjectSummary) => void }) {
  const { toast } = useToast();
  const [name, setName] = useState("");
  const [managerId, setManagerId] = useState("");
  const [managers, setManagers] = useState<ProjectManagerOption[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.get<ProjectManagerOption[]>("/api/vault/project-managers").then(setManagers).catch(() => {});
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const data = await api.post<{ id: number; name: string; manager: number }>("/api/vault/projects", {
        name, manager_id: Number(managerId),
      });
      onCreated({ id: data.id, name: data.name, manager: data.manager, created_at: new Date().toISOString() });
      toast(`Project "${data.name}" created.`);
      setName("");
      setManagerId("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create project");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-surface border border-sand-200 rounded-xl p-5 flex flex-col gap-4">
      <h2 className="text-sm font-semibold text-ink-700">New project</h2>
      <div className="grid sm:grid-cols-[1fr_1fr_auto] gap-3 items-end">
        <Input label="Project name" value={name} onChange={(e) => setName(e.target.value)} required />
        <Select label="Project Manager" value={managerId} onChange={(e) => setManagerId(e.target.value)} required>
          <option value="" disabled>Choose a Project Manager</option>
          {managers.map((m) => (
            <option key={m.id} value={m.id}>{m.username}</option>
          ))}
        </Select>
        <Button type="submit" loading={loading}>Create</Button>
      </div>
      {managers.length === 0 && (
        <p className="text-xs text-ink-400">No Project Manager accounts exist yet. Provision one from Admin first.</p>
      )}
      <ErrorMessage message={error} />
    </form>
  );
}
