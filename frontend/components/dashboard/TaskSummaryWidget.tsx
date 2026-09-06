"use client";

import { AlertTriangle, CalendarClock, CheckCircle2, ChevronRight, Clock, Hourglass, KeyRound } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Badge } from "@/components/shared/Badge";
import { api } from "@/lib/api";
import { TaskDetailItem, TaskSummary } from "@/lib/types";

interface Tile {
  key: keyof TaskSummary;
  label: string;
  icon: typeof Clock;
  tone: string;
}

const TILES: Tile[] = [
  { key: "pending_approvals", label: "Awaiting your approval", icon: Hourglass, tone: "text-warning-600 bg-warning-100" },
  { key: "open_issues", label: "Open issues in your projects", icon: AlertTriangle, tone: "text-danger-600 bg-danger-100" },
  { key: "my_pending_submissions", label: "Your submissions pending review", icon: Clock, tone: "text-accent-700 bg-accent-100" },
  { key: "expiring_soon", label: "Credentials expiring within 30 days", icon: CalendarClock, tone: "text-danger-600 bg-danger-100" },
  { key: "passwords_overdue_rotation", label: "Passwords overdue for rotation (90+ days)", icon: KeyRound, tone: "text-warning-600 bg-warning-100" },
];

export function TaskSummaryWidget() {
  const [summary, setSummary] = useState<TaskSummary | null>(null);
  const [expanded, setExpanded] = useState<keyof TaskSummary | null>(null);
  const [details, setDetails] = useState<Partial<Record<keyof TaskSummary, TaskDetailItem[]>>>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.get<TaskSummary>("/api/vault/tasks-summary").then(setSummary).catch(() => {});
  }, []);

  function toggle(key: keyof TaskSummary) {
    if (expanded === key) {
      setExpanded(null);
      return;
    }
    setExpanded(key);
    if (!details[key]) {
      setLoading(true);
      api.get<TaskDetailItem[]>(`/api/vault/tasks-summary/${key}`)
        .then((items) => setDetails((d) => ({ ...d, [key]: items })))
        .catch(() => setDetails((d) => ({ ...d, [key]: [] })))
        .finally(() => setLoading(false));
    }
  }

  if (!summary) return null;

  const total = summary.pending_approvals + summary.open_issues + summary.my_pending_submissions
    + summary.expiring_soon + summary.passwords_overdue_rotation;

  if (total === 0) {
    return (
      <div className="flex items-center gap-2 bg-success-100 border border-success-600/30 rounded-xl px-4 py-3 text-sm text-success-600">
        <CheckCircle2 size={18} /> Nothing needs your attention right now.
      </div>
    );
  }

  const activeTile = TILES.find((t) => t.key === expanded);
  const items = expanded ? details[expanded] : undefined;

  return (
    <div className="flex flex-col gap-3">
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {TILES.map((tile) => {
          const value = summary[tile.key];
          if (value === 0) return null;
          const Icon = tile.icon;
          const isOpen = expanded === tile.key;
          return (
            <button
              key={tile.key}
              onClick={() => toggle(tile.key)}
              className={`text-left bg-surface border rounded-xl p-4 flex items-center gap-3 transition-colors ${
                isOpen ? "border-accent-600/60 ring-1 ring-accent-600/30" : "border-sand-200 hover:border-accent-600/40"
              }`}
            >
              <div className={`w-9 h-9 rounded-full flex items-center justify-center shrink-0 ${tile.tone}`}>
                <Icon size={18} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-lg font-semibold text-ink-900">{value}</div>
                <div className="text-xs text-ink-500">{tile.label}</div>
              </div>
              <ChevronRight size={16} className={`text-ink-300 shrink-0 transition-transform ${isOpen ? "rotate-90" : ""}`} />
            </button>
          );
        })}
      </div>

      {activeTile && (
        <div className="bg-surface border border-sand-200 rounded-xl p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-400 mb-3">{activeTile.label}</h3>
          {loading && !items ? (
            <p className="text-sm text-ink-400">Loading...</p>
          ) : !items || items.length === 0 ? (
            <p className="text-sm text-ink-400">Nothing here.</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {items.map((item, i) => (
                <li
                  key={`${item.record_id}-${item.kind}-${i}`}
                  className="flex items-center justify-between gap-3 bg-sand-50 border border-sand-200 rounded-lg px-3 py-2 text-sm"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <Badge tone="accent">{item.platform_type.toLowerCase()}</Badge>
                      <span className="font-medium text-ink-800 truncate">{item.provider_name ?? "Untitled credential"}</span>
                    </div>
                    <p className="text-xs text-ink-500 truncate">
                      {item.project_name} &middot; {item.detail}
                    </p>
                  </div>
                  <Link
                    href={`/projects/${item.project_id}`}
                    className="shrink-0 text-xs text-accent-700 hover:underline whitespace-nowrap"
                  >
                    Open project
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
