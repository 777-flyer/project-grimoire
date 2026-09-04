"use client";

import { FormEvent, useState } from "react";

import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/shared/Button";
import { ErrorMessage } from "@/components/shared/ErrorMessage";
import { Input } from "@/components/shared/Input";

interface Step1Response {
  pending_ticket: string;
}

export function LoginForm({ onCredentialsAccepted }: { onCredentialsAccepted: (ticket: string) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const data = await api.post<Step1Response>("/api/auth/login/step1", { username, password });
      onCredentialsAccepted(data.pending_ticket);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <Input label="Username" value={username} onChange={(e) => setUsername(e.target.value)} required />
      <Input label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
      <ErrorMessage message={error} />
      <Button type="submit" loading={loading}>Continue</Button>
    </form>
  );
}
