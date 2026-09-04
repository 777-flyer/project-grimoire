"use client";

import { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "danger" | "ghost";

const variantClasses: Record<Variant, string> = {
  primary: "bg-accent-600 text-sand-50 hover:bg-accent-700",
  secondary: "bg-sand-50 text-ink-700 border border-sand-300 hover:bg-sand-200",
  danger: "bg-surface text-danger-600 border border-danger-600/40 hover:bg-danger-100",
  ghost: "bg-transparent text-ink-500 hover:text-ink-900",
};

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  loading?: boolean;
}

export function Button({ variant = "primary", loading, disabled, children, className = "", ...rest }: Props) {
  return (
    <button
      disabled={disabled || loading}
      className={`px-4 py-2 rounded-md font-medium text-sm transition-colors duration-150 disabled:opacity-40 disabled:cursor-not-allowed ${variantClasses[variant]} ${className}`}
      {...rest}
    >
      {loading ? "Working..." : children}
    </button>
  );
}
