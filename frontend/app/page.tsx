"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { api, ApiError } from "@/lib/api";

export const dynamic = "force-dynamic";

export default function RootPage() {
  const router = useRouter();

  useEffect(() => {
    api
      .get("/api/auth/profile")
      .then(() => router.replace("/dashboard"))
      .catch((err) => {
        if (err instanceof ApiError) router.replace("/login");
      });
  }, [router]);

  return (
    <main className="min-h-screen bg-background flex items-center justify-center text-ink-400 text-sm">
      Loading...
    </main>
  );
}
