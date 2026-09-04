"use client";

import { Copy, Eye, History } from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { AccessLogEntry } from "@/lib/types";

const FIELD_LABEL: Record<string, string> = {
  username: "Username", password: "Password", api_key: "API key",
};

export function AccessLogPanel({ projectId, recordId }: { projectId: number; recordId: number }) {
  const [open, setOpen] = useState(false);
  const [entries, setEntries] = useState<AccessLogEntry[] | null>(null);

  useEffect(() => {
    if (open && entries === null) {
      api.get<AccessLogEntry[]>(`/api/vault/projects/${projectId}/records/${recordId}/access-log`).then(setEntries).catch(() => {});
    }
  }, [open, entries, projectId, recordId]);

  return (
    <div>
      <button onClick={() => setOpen((v) => !v)} className="flex items-center gap-1.5 text-xs text-accent-700 hover:underline">
        <History size={13} /> {open ? "Hide access log" : "View access log"}
      </button>
      {open && (
        <div className="mt-2 bg-sand-50 border border-sand-200 rounded-lg p-3">
          {entries === null ? (
            <p className="text-sm text-ink-400">Loading...</p>
          ) : entries.length === 0 ? (
            <p className="text-sm text-ink-400">No one has revealed or copied a secret from this record yet.</p>
          ) : (
            <ul className="flex flex-col gap-1.5 text-sm">
              {entries.map((entry) => (
                <li key={entry.id} className="flex items-center gap-2 text-ink-700">
                  {entry.action === "REVEAL" ? <Eye size={13} className="text-ink-400" /> : <Copy size={13} className="text-ink-400" />}
                  <span>
                    user #{entry.user_id} {entry.action === "REVEAL" ? "revealed" : "copied"} the {FIELD_LABEL[entry.field_name] ?? entry.field_name} field
                  </span>
                  <span className="text-xs text-ink-400 ml-auto">{new Date(entry.accessed_at).toLocaleString()}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
