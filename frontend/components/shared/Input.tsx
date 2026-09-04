"use client";

import { InputHTMLAttributes } from "react";

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
}

export function Input({ label, id, className = "", ...rest }: Props) {
  const inputId = id || label.toLowerCase().replace(/\s+/g, "-");
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={inputId} className="text-sm font-medium text-ink-500">
        {label}
      </label>
      <input
        id={inputId}
        className={`bg-surface border border-sand-300 rounded-md px-3 py-2 text-sm text-ink-900 placeholder:text-ink-400 focus:outline-none focus:ring-2 focus:ring-accent-600/30 focus:border-accent-600 transition-colors duration-150 ${className}`}
        {...rest}
      />
    </div>
  );
}
