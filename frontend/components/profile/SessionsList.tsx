"use client";

import { Laptop, ShieldOff } from "lucide-react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { api, ApiError } from "@/lib/api";
import { Badge } from "@/components/shared/Badge";
import { Button } from "@/components/shared/Button";
import { ErrorMessage } from "@/components/shared/ErrorMessage";
import { useToast } from "@/lib/ToastContext";
import { SessionInfo } from "@/lib/types";

export function SessionsList() {
  const router = useRouter();
  const { toast } = useToast();
  const [sessions, setSessions] = useState<SessionInfo[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [revokingId, setRevokingId] = useState<number | null>(null);

  function refresh() {
    api.get<SessionInfo[]>("/api/auth/sessions").then(setSessions).catch(() => {});
  }

  useEffect(refresh, []);

  async function handleRevoke(session: SessionInfo) {
    setError(null);
    setRevokingId(session.id);
    try {
      await api.post(`/api/auth/sessions/${session.id}/revoke`);
      if (session.is_current) {
        toast("You've been logged out.", "info");
        router.push("/login");
        return;
      }
      toast("Session ended.");
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not end session");
    } finally {
      setRevokingId(null);
    }
  }

  return (
    <div className="bg-surface border border-sand-200 rounded-xl p-5 flex flex-col gap-3">
      <h2 className="text-sm font-semibold text-ink-700">Active sessions</h2>
      <p className="text-xs text-ink-400">
        Every device currently signed into your account. End any session you don&apos;t recognize.
      </p>
      {sessions === null ? (
        <p className="text-sm text-ink-400">Loading...</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {sessions.map((session) => (
            <li key={session.id} className="flex items-center justify-between bg-sand-50 border border-sand-200 rounded-lg px-3 py-2 text-sm">
              <div className="flex items-center gap-2">
                <Laptop size={16} className="text-ink-400" />
                <span className="font-mono text-xs text-ink-700">{session.device_label}</span>
                {session.is_current && <Badge tone="accent">this device</Badge>}
                <span className="text-xs text-ink-400">
                  since {new Date(session.created_at).toLocaleString()}
                </span>
              </div>
              <Button
                variant="danger"
                loading={revokingId === session.id}
                onClick={() => handleRevoke(session)}
              >
                <ShieldOff size={14} className="inline mr-1" />
                {session.is_current ? "Log out" : "End session"}
              </Button>
            </li>
          ))}
        </ul>
      )}
      <ErrorMessage message={error} />
    </div>
  );
}
