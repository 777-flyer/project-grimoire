"use client";

import { useEffect, useState } from "react";

import { CreateUserForm } from "@/components/admin/CreateUserForm";
import { UserList } from "@/components/admin/UserList";
import { useAuth } from "@/lib/AuthContext";
import { api } from "@/lib/api";
import { AdminUser, Role } from "@/lib/types";

export default function AdminPage() {
  const profile = useAuth();
  const [users, setUsers] = useState<AdminUser[] | null>(null);
  const [lastCreated, setLastCreated] = useState<{ username: string; secret: string; role: Role } | null>(null);

  useEffect(() => {
    if (profile.role === "SUPER_ADMIN") {
      api.get<AdminUser[]>("/api/auth/admin/users").then(setUsers).catch(() => {});
    }
  }, [profile.role]);

  if (profile.role !== "SUPER_ADMIN") {
    return <main className="max-w-3xl mx-auto px-6 py-10 text-sm text-ink-400">Forbidden.</main>;
  }

  return (
    <main className="max-w-4xl mx-auto px-6 py-10 flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-semibold text-ink-900">Admin</h1>
        <p className="text-sm text-ink-500 mt-1">Provision accounts for every role in the company.</p>
      </div>

      <CreateUserForm
        onCreated={(result) => {
          setLastCreated({ username: result.username, secret: result.totp_secret_base32, role: result.role });
          api.get<AdminUser[]>("/api/auth/admin/users").then(setUsers).catch(() => {});
        }}
      />

      {lastCreated && (
        <div className="bg-accent-100 border border-accent-600/30 rounded-xl p-4 text-sm">
          <p className="text-ink-700 mb-2">
            Give this TOTP secret to <strong>{lastCreated.username}</strong> ({lastCreated.role.replace("_", " ")}) so they can
            confirm it before logging in:
          </p>
          <code className="text-xs break-all bg-surface px-2 py-1 rounded border border-sand-300">{lastCreated.secret}</code>
        </div>
      )}

      {users === null ? (
        <p className="text-sm text-ink-400">Loading...</p>
      ) : (
        <UserList users={users} />
      )}
    </main>
  );
}
