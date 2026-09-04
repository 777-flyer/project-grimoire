"use client";

import { FormEvent, useState } from "react";

import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/shared/Button";
import { ErrorMessage } from "@/components/shared/ErrorMessage";
import { Input } from "@/components/shared/Input";

interface RegisterResponse {
  user_id: number;
  totp_secret_base32: string;
  totp_issuer: string;
}

interface RegisterResult extends RegisterResponse {
  username: string;
}

export function RegisterForm({ onRegistered }: { onRegistered: (data: RegisterResult) => void }) {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [contact, setContact] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const data = await api.post<RegisterResponse>("/api/auth/register", {
        username, email, contact, password,
      });
      onRegistered({ ...data, username });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <Input label="Username" value={username} onChange={(e) => setUsername(e.target.value)} required />
      <Input label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
      <Input label="Contact" value={contact} onChange={(e) => setContact(e.target.value)} />
      <Input
        label="Password"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
        minLength={10}
      />
      <ErrorMessage message={error} />
      <Button type="submit" loading={loading}>Create account</Button>
    </form>
  );
}
