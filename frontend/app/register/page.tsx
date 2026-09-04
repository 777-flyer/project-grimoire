"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Card } from "@/components/shared/Card";
import { RegisterForm } from "@/components/register/RegisterForm";
import { TotpSetup } from "@/components/register/TotpSetup";

interface RegisteredState {
  userId: number;
  username: string;
  secretBase32: string;
  issuer: string;
}

export default function RegisterPage() {
  const router = useRouter();
  const [registered, setRegistered] = useState<RegisteredState | null>(null);

  return (
    <main className="min-h-screen bg-background flex items-center justify-center px-4">
      <Card className="w-full max-w-md">
        <h1 className="text-xl font-semibold mb-1 text-ink-900">
          {registered ? "Set up two-factor authentication" : "Create your Grimoire account"}
        </h1>
        <p className="text-sm text-ink-500 mb-6">
          {registered
            ? "One more step before you can log in."
            : "Every field you enter is encrypted before it's stored."}
        </p>

        {!registered ? (
          <RegisterForm
            onRegistered={(data) => {
              setRegistered({
                userId: data.user_id,
                username: data.username,
                secretBase32: data.totp_secret_base32,
                issuer: data.totp_issuer,
              });
            }}
          />
        ) : (
          <TotpSetup
            userId={registered.userId}
            username={registered.username}
            secretBase32={registered.secretBase32}
            issuer={registered.issuer}
            onConfirmed={() => router.push("/login")}
          />
        )}

        {!registered && (
          <p className="text-sm text-ink-500 mt-4">
            Already have an account? <Link href="/login" className="text-accent-700 hover:underline">Log in</Link>
          </p>
        )}
      </Card>
    </main>
  );
}
