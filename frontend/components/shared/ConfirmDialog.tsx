"use client";

import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/shared/Button";

interface Props {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({ open, title, description, confirmLabel = "Confirm", loading, onConfirm, onCancel }: Props) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/40 px-4">
      <div className="bg-surface-raised border border-sand-200 rounded-xl p-6 max-w-sm w-full shadow-lg">
        <div className="flex items-start gap-3">
          <div className="w-9 h-9 rounded-full bg-danger-100 text-danger-600 flex items-center justify-center shrink-0">
            <AlertTriangle size={18} />
          </div>
          <div>
            <h2 className="font-semibold text-ink-900">{title}</h2>
            <p className="text-sm text-ink-500 mt-1">{description}</p>
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <Button variant="secondary" onClick={onCancel}>Cancel</Button>
          <Button variant="danger" loading={loading} onClick={onConfirm}>{confirmLabel}</Button>
        </div>
      </div>
    </div>
  );
}
