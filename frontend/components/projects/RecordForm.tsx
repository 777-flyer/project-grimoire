"use client";

import { FormEvent, useState } from "react";

import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/shared/Button";
import { ErrorMessage } from "@/components/shared/ErrorMessage";
import { Input } from "@/components/shared/Input";
import { Select } from "@/components/shared/Select";
import { useAuth } from "@/lib/AuthContext";
import { useToast } from "@/lib/ToastContext";
import { Environment, PlatformType, RecordSummary } from "@/lib/types";

const PLATFORM_OPTIONS: { value: PlatformType; label: string }[] = [
  { value: "DOMAIN", label: "Domain" },
  { value: "HOSTING", label: "Hosting" },
  { value: "EMAIL", label: "Email" },
  { value: "OTHER", label: "Other" },
];

const ENVIRONMENT_OPTIONS: { value: Environment; label: string }[] = [
  { value: "PRODUCTION", label: "Production" },
  { value: "STAGING", label: "Staging" },
  { value: "DEVELOPMENT", label: "Development" },
];

export function RecordForm({ projectId, onCreated }: { projectId: number; onCreated: (record: RecordSummary) => void }) {
  const profile = useAuth();
  const { toast } = useToast();
  const autoApproved = profile.role === "SUPER_ADMIN" || profile.role === "PROJECT_MANAGER";
  const [platformType, setPlatformType] = useState<PlatformType>("HOSTING");
  const [environment, setEnvironment] = useState<Environment>("PRODUCTION");
  const [providerName, setProviderName] = useState("");
  const [loginUrl, setLoginUrl] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [expiresOn, setExpiresOn] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const record = await api.post<RecordSummary>(`/api/vault/projects/${projectId}/records`, {
        platform_type: platformType, provider_name: providerName, environment,
        login_url: loginUrl, username, password, api_key: apiKey,
        expires_on: expiresOn || null,
      });
      onCreated(record);
      toast(autoApproved ? "Credential added." : "Submitted for approval.");
      setProviderName(""); setLoginUrl(""); setUsername(""); setPassword(""); setApiKey(""); setExpiresOn("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create record");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-surface border border-sand-200 rounded-xl p-5 flex flex-col gap-4">
      <h2 className="text-sm font-semibold text-ink-700">Add a purchased credential</h2>
      <div className="grid sm:grid-cols-2 gap-3">
        <Select label="Platform" value={platformType} onChange={(e) => setPlatformType(e.target.value as PlatformType)}>
          {PLATFORM_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </Select>
        <Select label="Environment" value={environment} onChange={(e) => setEnvironment(e.target.value as Environment)}>
          {ENVIRONMENT_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </Select>
        <Input label="Provider name" placeholder="e.g. GoDaddy, AWS, Google Workspace" value={providerName} onChange={(e) => setProviderName(e.target.value)} required />
        <Input label="Login URL" value={loginUrl} onChange={(e) => setLoginUrl(e.target.value)} />
        <Input label="Username" value={username} onChange={(e) => setUsername(e.target.value)} />
        <Input label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        <Input label="API key" value={apiKey} onChange={(e) => setApiKey(e.target.value)} />
        <Input label="Expires on" type="date" value={expiresOn} onChange={(e) => setExpiresOn(e.target.value)} />
      </div>
      <ErrorMessage message={error} />
      <div>
        <Button type="submit" loading={loading}>{autoApproved ? "Add credential" : "Submit for approval"}</Button>
      </div>
    </form>
  );
}
