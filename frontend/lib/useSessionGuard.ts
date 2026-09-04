"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api, ApiError } from "@/lib/api";
import { Profile } from "@/lib/types";

/** Re-checks the session on mount and on bfcache restore (browser back button). */
export function useSessionGuard() {
  const router = useRouter();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function check() {
      try {
        const data = await api.get<Profile>("/api/auth/profile");
        if (!cancelled) {
          setProfile(data);
          setChecked(true);
        }
      } catch (err) {
        if (!cancelled && err instanceof ApiError && err.status === 401) {
          router.replace("/login");
        }
      }
    }

    check();

    function handlePageShow(event: PageTransitionEvent) {
      if (event.persisted) {
        // Hide stale bfcache content before re-verifying.
        setChecked(false);
        setProfile(null);
        check();
      }
    }

    window.addEventListener("pageshow", handlePageShow);
    return () => {
      cancelled = true;
      window.removeEventListener("pageshow", handlePageShow);
    };
  }, [router]);

  return { profile, checked };
}
