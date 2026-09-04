"use client";

import { ReactNode } from "react";

import { AuthContext } from "@/lib/AuthContext";
import { useSessionGuard } from "@/lib/useSessionGuard";
import { NavBar } from "@/components/shared/NavBar";

/** Wraps every authenticated route; blocks rendering until the session is verified. */
export function AuthGuard({ children }: { children: ReactNode }) {
  const { profile, checked } = useSessionGuard();

  if (!checked || !profile) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center text-ink-400 text-sm">
        Checking session...
      </div>
    );
  }

  return (
    <AuthContext.Provider value={profile}>
      <div className="min-h-screen bg-background">
        <NavBar role={profile.role} username={profile.username} />
        {children}
      </div>
    </AuthContext.Provider>
  );
}
