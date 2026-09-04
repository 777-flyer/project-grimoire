"use client";

import { ProfileForm } from "@/components/profile/ProfileForm";
import { SessionsList } from "@/components/profile/SessionsList";
import { useAuth } from "@/lib/AuthContext";

export default function ProfilePage() {
  const profile = useAuth();

  return (
    <main className="max-w-3xl mx-auto px-6 py-10 flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-ink-900">Profile &amp; security</h1>
        <p className="text-sm text-ink-500 mt-1">Manage your account details and active sessions.</p>
      </div>
      <ProfileForm profile={profile} />
      <SessionsList />
    </main>
  );
}
