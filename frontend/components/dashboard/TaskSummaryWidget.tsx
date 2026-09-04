"use client";

import { AlertTriangle, CalendarClock, CheckCircle2, Clock, Hourglass, KeyRound } from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { TaskSummary } from "@/lib/types";

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

  useEffect(() => {
    api.get<TaskSummary>("/api/vault/tasks-summary").then(setSummary).catch(() => {});
  }, []);

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

  return (
    <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
      {TILES.map((tile) => {
        const value = summary[tile.key];
        if (value === 0) return null;
        const Icon = tile.icon;
        return (
          <div key={tile.key} className="bg-surface border border-sand-200 rounded-xl p-4 flex items-center gap-3">
            <div className={`w-9 h-9 rounded-full flex items-center justify-center shrink-0 ${tile.tone}`}>
              <Icon size={18} />
            </div>
            <div>
              <div className="text-lg font-semibold text-ink-900">{value}</div>
              <div className="text-xs text-ink-500">{tile.label}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
