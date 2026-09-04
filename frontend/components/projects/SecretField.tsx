"use client";

import { Check, Copy, Eye, EyeOff } from "lucide-react";
import { useState } from "react";

import { api } from "@/lib/api";

interface Props {
  value: string | null;
  projectId: number;
  recordId: number;
  fieldName: string;
}

export function SecretField({ value, projectId, recordId, fieldName }: Props) {
  const [revealed, setRevealed] = useState(false);
  const [copied, setCopied] = useState(false);

  if (value === null) {
    return <span className="text-ink-400 italic">restricted</span>;
  }
  if (!value) {
    return <span className="text-ink-400">—</span>;
  }

  function logAccess(action: "REVEAL" | "COPY") {
    // Fire-and-forget: the audit trail shouldn't block or fail the UI action itself.
    api.post(`/api/vault/projects/${projectId}/records/${recordId}/access-log`, { field_name: fieldName, action }).catch(() => {});
  }

  function handleReveal() {
    setRevealed((v) => {
      if (!v) logAccess("REVEAL");
      return !v;
    });
  }

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(value as string);
      setCopied(true);
      logAccess("COPY");
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard access denied; nothing sensible to do beyond leaving the icon unchanged
    }
  }

  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="font-mono">{revealed ? value : "•".repeat(Math.min(value.length, 12))}</span>
      <button
        type="button"
        onClick={handleReveal}
        className="text-ink-400 hover:text-ink-700 transition-colors"
        title={revealed ? "Hide" : "Reveal"}
      >
        {revealed ? <EyeOff size={13} /> : <Eye size={13} />}
      </button>
      <button
        type="button"
        onClick={handleCopy}
        className="text-ink-400 hover:text-ink-700 transition-colors"
        title="Copy to clipboard"
      >
        {copied ? <Check size={13} className="text-success-600" /> : <Copy size={13} />}
      </button>
    </span>
  );
}
