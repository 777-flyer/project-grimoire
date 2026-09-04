"use client";

import { FormEvent, useState } from "react";

import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/shared/Button";
import { ErrorMessage } from "@/components/shared/ErrorMessage";
import { Input } from "@/components/shared/Input";

export function RecordNoteForm({ projectId, recordId, onAdded }: { projectId: number; recordId: number; onAdded: () => void }) {
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.post(`/api/vault/projects/${projectId}/records/${recordId}/notes`, { text });
      setText("");
      onAdded();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not add note");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-end gap-2">
      <div className="flex-1">
        <Input label="Add a maintenance note" value={text} onChange={(e) => setText(e.target.value)} required />
      </div>
      <Button type="submit" variant="secondary" loading={loading}>Add</Button>
      <ErrorMessage message={error} />
    </form>
  );
}
