"use client";

import { KeyRound } from "lucide-react";
import { useState } from "react";

import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/shared/Button";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { ErrorMessage } from "@/components/shared/ErrorMessage";
import { useToast } from "@/lib/ToastContext";

export function RotateKeyButton({ projectId }: { projectId: number }) {
  const { toast } = useToast();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [confirming, setConfirming] = useState(false);

  async function handleConfirm() {
    setError(null);
    setLoading(true);
    try {
      await api.post(`/api/vault/projects/${projectId}/rotate`);
      toast("Project key rotated. Every record was re-encrypted.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not rotate key");
    } finally {
      setLoading(false);
      setConfirming(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div>
        <Button variant="secondary" onClick={() => setConfirming(true)}>
          <KeyRound size={14} className="inline mr-1" /> Rotate project key
        </Button>
      </div>
      <ErrorMessage message={error} />
      <ConfirmDialog
        open={confirming}
        title="Rotate the project key?"
        description="Generates a new keypair, re-encrypts every credential record, and re-issues access to every current member. Old keys are retired immediately."
        confirmLabel="Rotate key"
        loading={loading}
        onConfirm={handleConfirm}
        onCancel={() => setConfirming(false)}
      />
    </div>
  );
}
