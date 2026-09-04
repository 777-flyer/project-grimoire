"use client";

import { SelectHTMLAttributes } from "react";

interface Props extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
}

export function Select({ label, id, className = "", children, ...rest }: Props) {
  const selectId = id || label.toLowerCase().replace(/\s+/g, "-");
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={selectId} className="text-sm font-medium text-ink-500">
        {label}
      </label>
      <select
        id={selectId}
        className={`bg-surface border border-sand-300 rounded-md px-3 py-2 text-sm text-ink-900 focus:outline-none focus:ring-2 focus:ring-accent-600/30 focus:border-accent-600 transition-colors duration-150 ${className}`}
        {...rest}
      >
        {children}
      </select>
    </div>
  );
}
