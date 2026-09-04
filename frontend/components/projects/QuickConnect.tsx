"use client";

import { Check, Copy, ExternalLink, Terminal } from "lucide-react";
import { useState } from "react";

import { PlatformType } from "@/lib/types";

function extractHost(url: string): string {
  try {
    return new URL(url.includes("://") ? url : `https://${url}`).hostname;
  } catch {
    return url;
  }
}

function buildConnection(platformType: PlatformType, loginUrl: string, username: string | null) {
  if (!loginUrl) return null;

  if (platformType === "HOSTING") {
    const host = extractHost(loginUrl);
    return { kind: "command" as const, value: username ? `ssh ${username}@${host}` : `ssh ${host}` };
  }
  if (platformType === "EMAIL") {
    return { kind: "link" as const, value: loginUrl, label: "Open webmail" };
  }
  if (platformType === "DOMAIN") {
    return { kind: "link" as const, value: loginUrl, label: "Open registrar" };
  }
  return { kind: "link" as const, value: loginUrl, label: "Open" };
}

export function QuickConnect({ platformType, loginUrl, username }: { platformType: PlatformType; loginUrl: string; username: string | null }) {
  const [copied, setCopied] = useState(false);
  const connection = buildConnection(platformType, loginUrl, username);
  if (!connection) return null;

  if (connection.kind === "link") {
    const href = connection.value.includes("://") ? connection.value : `https://${connection.value}`;
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1.5 text-xs text-accent-700 hover:underline"
      >
        <ExternalLink size={13} /> {connection.label}
      </a>
    );
  }

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(connection!.value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard access denied; nothing sensible to do beyond leaving the icon unchanged
    }
  }

  return (
    <button
      onClick={handleCopy}
      className="inline-flex items-center gap-1.5 text-xs text-accent-700 hover:underline font-mono"
      title="Copy connect command"
    >
      <Terminal size={13} /> {connection.value}
      {copied ? <Check size={12} className="text-success-600" /> : <Copy size={12} />}
    </button>
  );
}
