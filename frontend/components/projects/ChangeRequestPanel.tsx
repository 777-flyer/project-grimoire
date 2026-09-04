"use client";

import { FormEvent, useEffect, useState } from "react";

import { api, ApiError } from "@/lib/api";
import { Badge } from "@/components/shared/Badge";
import { Button } from "@/components/shared/Button";
import { ErrorMessage } from "@/components/shared/ErrorMessage";
import { Input } from "@/components/shared/Input";
import { useToast } from "@/lib/ToastContext";
import { ChangeRequestSummary, CredentialFields } from "@/lib/types";

const STATUS_TONE = { PENDING: "warning", APPROVED: "success", REJECTED: "danger" } as const;

interface Props {
  projectId: number;
  recordId: number;
  canManage: boolean;
  onApplied: () => void;
}

export function ChangeRequestPanel({ projectId, recordId, canManage, onApplied }: Props) {
  const { toast } = useToast();
  const [requests, setRequests] = useState<ChangeRequestSummary[] | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [providerName, setProviderName] = useState("");
  const [loginUrl, setLoginUrl] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const base = `/api/vault/projects/${projectId}/records/${recordId}/change-requests`;

  function refresh() {
    api.get<ChangeRequestSummary[]>(base).then(setRequests).catch(() => {});
  }

  useEffect(refresh, [projectId, recordId]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const edits: Partial<CredentialFields> = {};
    if (providerName) edits.provider_name = providerName;
    if (loginUrl) edits.login_url = loginUrl;
    if (username) edits.username = username;
    if (password) edits.password = password;
    if (apiKey) edits.api_key = apiKey;
    try {
      const cr = await api.post<ChangeRequestSummary>(base, edits);
      setShowForm(false);
      setProviderName(""); setLoginUrl(""); setUsername(""); setPassword(""); setApiKey("");
      refresh();
      onApplied();
      toast(cr.status === "APPROVED" ? "Change applied." : "Change request submitted for approval.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not submit change");
    } finally {
      setLoading(false);
    }
  }

  async function handleReview(id: number, action: "approve" | "reject") {
    setError(null);
    try {
      await api.post(`${base}/${id}/${action}`);
      refresh();
      onApplied();
      toast(action === "approve" ? "Change request approved and applied." : "Change request rejected.", action === "approve" ? "success" : "info");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not review change request");
    }
  }

  const pending = (requests ?? []).filter((r) => r.status === "PENDING");

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-400">Change requests</h3>
        <button onClick={() => setShowForm((v) => !v)} className="text-xs text-accent-700 hover:underline">
          {showForm ? "Cancel" : "Propose a change"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="grid sm:grid-cols-2 gap-2 bg-sand-50 border border-sand-200 rounded-lg p-3">
          <Input label="Provider name" value={providerName} onChange={(e) => setProviderName(e.target.value)} placeholder="unchanged" />
          <Input label="Login URL" value={loginUrl} onChange={(e) => setLoginUrl(e.target.value)} placeholder="unchanged" />
          <Input label="Username" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="unchanged" />
          <Input label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="unchanged" />
          <Input label="API key" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="unchanged" />
          <div className="sm:col-span-2">
            <Button type="submit" variant="secondary" loading={loading}>Submit change request</Button>
          </div>
        </form>
      )}

      {pending.length > 0 && (
        <ul className="flex flex-col gap-2">
          {pending.map((cr) => (
            <li key={cr.id} className="text-sm bg-warning-100 border border-warning-600/30 rounded-lg px-3 py-2 flex items-center justify-between gap-3">
              <div>
                <Badge tone={STATUS_TONE[cr.status]}>{cr.status}</Badge>
                <span className="ml-2 text-ink-700">
                  proposed by user #{cr.submitted_by} &middot; {new Date(cr.created_at).toLocaleString()}
                </span>
              </div>
              {canManage && (
                <div className="flex gap-2">
                  <Button variant="secondary" onClick={() => handleReview(cr.id, "approve")}>Approve</Button>
                  <Button variant="danger" onClick={() => handleReview(cr.id, "reject")}>Reject</Button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
      <ErrorMessage message={error} />
    </div>
  );
}
