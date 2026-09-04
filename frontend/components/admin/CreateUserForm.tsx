"use client";

import { FormEvent, useState } from "react";

import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/shared/Button";
import { ErrorMessage } from "@/components/shared/ErrorMessage";
import { Input } from "@/components/shared/Input";
import { Select } from "@/components/shared/Select";
import { useToast } from "@/lib/ToastContext";
import { Role } from "@/lib/types";

const ROLES: { value: Role; label: string }[] = [
  { value: "PROJECT_MANAGER", label: "Project Manager" },
  { value: "DEVOPS_ENGINEER", label: "DevOps Engineer" },
  { value: "BACKEND_DEVELOPER", label: "Backend Developer" },
  { value: "SUPER_ADMIN", label: "Super Admin" },
];

interface CreateResponse {
  user_id: number;
  role: Role;
  totp_secret_base32: string;
}

export function CreateUserForm({ onCreated }: { onCreated: (result: CreateResponse & { username: string }) => void }) {
  const { toast } = useToast();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [contact, setContact] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("DEVOPS_ENGINEER");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const data = await api.post<CreateResponse>("/api/auth/admin/users/create", {
        username, email, contact, password, role,
      });
      onCreated({ ...data, username });
      toast(`${username} provisioned as ${role.replace("_", " ")}.`);
      setUsername(""); setEmail(""); setContact(""); setPassword("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create user");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-surface border border-sand-200 rounded-xl p-5 flex flex-col gap-4">
      <h2 className="text-sm font-semibold text-ink-700">Provision a user</h2>
      <div className="grid sm:grid-cols-2 gap-3">
        <Input label="Username" value={username} onChange={(e) => setUsername(e.target.value)} required />
        <Input label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <Input label="Contact" value={contact} onChange={(e) => setContact(e.target.value)} />
        <Input label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={10} />
      </div>
      <Select label="Role" value={role} onChange={(e) => setRole(e.target.value as Role)}>
        {ROLES.map((r) => (
          <option key={r.value} value={r.value}>{r.label}</option>
        ))}
      </Select>
      <ErrorMessage message={error} />
      <div>
        <Button type="submit" loading={loading}>Create user</Button>
      </div>
    </form>
  );
}
