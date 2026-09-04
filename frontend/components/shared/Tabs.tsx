"use client";

import type { LucideIcon } from "lucide-react";

interface Tab {
  key: string;
  label: string;
  icon?: LucideIcon;
  count?: number;
}

interface Props {
  tabs: Tab[];
  active: string;
  onChange: (key: string) => void;
}

export function Tabs({ tabs, active, onChange }: Props) {
  return (
    <div className="flex gap-1 border-b border-sand-200">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        return (
          <button
            key={tab.key}
            onClick={() => onChange(tab.key)}
            className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors duration-150 ${
              active === tab.key
                ? "border-accent-600 text-accent-700"
                : "border-transparent text-ink-500 hover:text-ink-900"
            }`}
          >
            {Icon && <Icon size={15} />}
            {tab.label}
            {tab.count !== undefined && tab.count > 0 && (
              <span className="ml-1 text-xs bg-sand-200 text-ink-700 rounded-full px-1.5 py-0.5">{tab.count}</span>
            )}
          </button>
        );
      })}
    </div>
  );
}
