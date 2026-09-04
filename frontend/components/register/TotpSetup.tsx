"use client";

import { FormEvent, useState } from "react";

import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/shared/Button";
import { ErrorMessage } from "@/components/shared/ErrorMessage";
import { Input } from "@/components/shared/Input";

interface Props {
  userId: number;
  secretBase32: string;
  issuer: string;
  username: string;
  onConfirmed: () => void;
}

export function TotpSetup({ userId, secretBase32, issuer, username, onConfirmed }: Props) {
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // No algorithm parameter: authenticator apps use SHA1 for TOTP regardless.
  const otpauthUri = `otpauth://totp/${encodeURIComponent(issuer)}:${encodeURIComponent(username)}?secret=${secretBase32}&issuer=${encodeURIComponent(issuer)}`;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.post("/api/auth/totp/confirm", { user_id: userId, code });
      onConfirmed();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Confirmation failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-ink-700">
        Add this secret to an authenticator app (Google Authenticator, Authy, etc.), then enter the
        6-digit code it produces.
      </p>
      <div className="bg-sand-50 border border-sand-300 rounded-md p-3 text-xs font-mono break-all text-accent-700">
        {secretBase32}
      </div>
      <details className="text-xs text-ink-400">
        <summary className="cursor-pointer">otpauth:// URI (for QR code generators)</summary>
        <div className="mt-2 break-all">{otpauthUri}</div>
      </details>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <Input label="6-digit code" value={code} onChange={(e) => setCode(e.target.value)} maxLength={6} required />
        <ErrorMessage message={error} />
        <Button type="submit" loading={loading}>Confirm and finish setup</Button>
      </form>
    </div>
  );
}
