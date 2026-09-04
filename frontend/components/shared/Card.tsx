import { ReactNode } from "react";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`bg-surface border border-sand-200 rounded-xl shadow-sm shadow-ink-900/5 p-6 ${className}`}>
      {children}
    </div>
  );
}
