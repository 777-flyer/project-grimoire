"use client";

import { Pencil } from "lucide-react";
import { useState } from "react";

import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/shared/Button";
import { ErrorMessage } from "@/components/shared/ErrorMessage";
import { Select } from "@/components/shared/Select";
import { useToast } from "@/lib/ToastContext";
import { Environment, RecordSummary } from "@/lib/types";

const ENVIRONMENT_OPTIONS: { value: Environment; label: string }[] = [
  { value: "PRODUCTION", label: "Production" },
  { value: "STAGING", label: "Staging" },
  { value: "DEVELOPMENT", label: "Development" },
];

interface Props {
  projectId: number;
  record: RecordSummary;
  onUpdated: (record: RecordSummary) => void;
}

export function MetadataEditor({ projectId, record, onUpdated }: Props) {
  const { toast } = useToast();
  const [editing, setEditing] = useState(false);
  const [environment, setEnvironment] = useState<Environment>(record.environment);
  const [expiresOn, setExpiresOn] = useState(record.expires_on ?? "");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSave() {
    setError(null);
    setLoading(true);
    try {
      const updated = await api.post<RecordSummary>(
        `/api/vault/projects/${projectId}/records/${record.id}/metadata`,
        { environment, expires_on: expiresOn || "" }
      );
      onUpdated(updated);
      setEditing(false);
      toast("Details updated.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not update");
    } finally {
      setLoading(false);
    }
  }

  if (!editing) {
    return (
      <button onClick={() => setEditing(true)} className="text-ink-400 hover:text-ink-700 transition-colors" title="Edit environment/expiry">
        <Pencil size={13} />
      </button>
    );
  }

  return (
    <div className="flex flex-col gap-2 bg-sand-50 border border-sand-200 rounded-lg p-3 w-full sm:w-auto">
      <div className="flex flex-wrap items-end gap-2">
        <Select id={`metadata-environment-${record.id}`} label="Environment" value={environment} onChange={(e) => setEnvironment(e.target.value as Environment)} className="w-40">
          {ENVIRONMENT_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </Select>
        <div className="flex flex-col gap-1">
          <label htmlFor={`expiry-date-${record.id}`} className="text-sm font-medium text-ink-500">Expires on</label>
          <input
            id={`expiry-date-${record.id}`}
            type="date"
            value={expiresOn}
            onChange={(e) => setExpiresOn(e.target.value)}
            className="bg-surface border border-sand-300 rounded-md px-3 py-2 text-sm text-ink-900 focus:outline-none focus:ring-2 focus:ring-accent-600/30 focus:border-accent-600"
          />
        </div>
        <Button loading={loading} onClick={handleSave}>Save</Button>
        <Button variant="secondary" onClick={() => setEditing(false)}>Cancel</Button>
      </div>
      <ErrorMessage message={error} />
    </div>
  );
}
