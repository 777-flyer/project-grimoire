"use client";

import { FormEvent, useState } from "react";

import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/shared/Button";
import { ErrorMessage } from "@/components/shared/ErrorMessage";
import { Input } from "@/components/shared/Input";
import { useToast } from "@/lib/ToastContext";
import { Profile } from "@/lib/types";

export function ProfileForm({ profile }: { profile: Profile }) {
  const { toast } = useToast();
  const [username, setUsername] = useState(profile.username);
  const [email, setEmail] = useState(profile.email);
  const [contact, setContact] = useState(profile.contact);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.put("/api/auth/profile", { username, email, contact });
      toast("Profile updated.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not update profile");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-surface border border-sand-200 rounded-xl p-5 flex flex-col gap-4">
      <h2 className="text-sm font-semibold text-ink-700">Your profile</h2>
      <div className="grid sm:grid-cols-2 gap-3">
        <Input label="Username" value={username} onChange={(e) => setUsername(e.target.value)} required />
        <Input label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <Input label="Contact" value={contact} onChange={(e) => setContact(e.target.value)} />
      </div>
      <ErrorMessage message={error} />
      <div>
        <Button type="submit" loading={loading}>Save changes</Button>
      </div>
    </form>
  );
}
