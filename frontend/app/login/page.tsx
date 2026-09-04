"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Card } from "@/components/shared/Card";
import { LoginForm } from "@/components/login/LoginForm";
import { TotpPrompt } from "@/components/login/TotpPrompt";

export const dynamic = "force-dynamic";

export default function LoginPage() {
  const router = useRouter();
  const [ticket, setTicket] = useState<string | null>(null);

  return (
    <main className="min-h-screen bg-background flex items-center justify-center px-4">
      <Card className="w-full max-w-md">
        <div className="flex items-center gap-2 mb-1">
          <span className="w-7 h-7 rounded-md bg-accent-600 flex items-center justify-center text-sand-50 text-sm font-bold">
            G
          </span>
          <h1 className="text-xl font-semibold text-ink-900">Grimoire</h1>
        </div>
        <p className="text-sm text-ink-500 mb-6">
          {ticket ? "Enter your authenticator code." : "Sign in to your vault."}
        </p>

        {!ticket ? (
          <LoginForm onCredentialsAccepted={setTicket} />
        ) : (
          <TotpPrompt ticket={ticket} onVerified={() => router.replace("/dashboard")} />
        )}

        {!ticket && (
          <p className="text-sm text-ink-500 mt-4">
            No account? <Link href="/register" className="text-accent-700 hover:underline">Register</Link>
          </p>
        )}
      </Card>
    </main>
  );
}
