"use client";

import { FormEvent, useState } from "react";

import { api, ApiError } from "@/lib/api";
import { Badge } from "@/components/shared/Badge";
import { Button } from "@/components/shared/Button";
import { ErrorMessage } from "@/components/shared/ErrorMessage";
import { Input } from "@/components/shared/Input";
import { Select } from "@/components/shared/Select";
import { useAuth } from "@/lib/AuthContext";
import { useToast } from "@/lib/ToastContext";
import { NoteKind, RecordNote } from "@/lib/types";

const ROLE_LABEL: Record<string, string> = {
  SUPER_ADMIN: "Admin", PROJECT_MANAGER: "PM", DEVOPS_ENGINEER: "DevOps", BACKEND_DEVELOPER: "Backend",
};

interface Props {
  projectId: number;
  recordId: number;
  notes: RecordNote[];
  onChanged: () => void;
}

export function NotesThread({ projectId, recordId, notes, onChanged }: Props) {
  const profile = useAuth();
  const { toast } = useToast();
  const [text, setText] = useState("");
  const [kind, setKind] = useState<NoteKind>("note");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const canResolve = profile.role !== "BACKEND_DEVELOPER";

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.post(`/api/vault/projects/${projectId}/records/${recordId}/notes`, { text, kind });
      setText("");
      onChanged();
      toast(kind === "issue" ? "Issue reported." : "Note added.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not post");
    } finally {
      setLoading(false);
    }
  }

  async function handleResolve(noteId: string) {
    setError(null);
    try {
      await api.post(`/api/vault/projects/${projectId}/records/${recordId}/notes/${noteId}/resolve`);
      onChanged();
      toast("Issue marked resolved.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not resolve");
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-400">Notes &amp; issues</h3>

      {notes.length === 0 ? (
        <p className="text-sm text-ink-400">No notes yet.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {notes.map((note) => (
            <li key={note.id} className="text-sm bg-sand-50 border border-sand-200 rounded-lg px-3 py-2">
              <div className="flex items-center justify-between gap-2 mb-1">
                <div className="flex items-center gap-2">
                  <Badge tone={note.kind === "issue" ? (note.status === "resolved" ? "success" : "danger") : "neutral"}>
                    {note.kind === "issue" ? (note.status === "resolved" ? "resolved" : "open issue") : "note"}
                  </Badge>
                  <span className="text-ink-400 text-xs">
                    {ROLE_LABEL[note.author_role] ?? note.author_role} &middot; {new Date(note.at).toLocaleString()}
                  </span>
                </div>
                {note.kind === "issue" && note.status === "open" && canResolve && (
                  <button
                    onClick={() => handleResolve(note.id)}
                    className="text-xs text-accent-700 hover:underline"
                  >
                    Mark resolved
                  </button>
                )}
              </div>
              <p className="text-ink-700">{note.text}</p>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={handleSubmit} className="flex items-end gap-2">
        <div className="flex-1">
          <Input label="Add a note or issue" value={text} onChange={(e) => setText(e.target.value)} required />
        </div>
        <Select label="Type" value={kind} onChange={(e) => setKind(e.target.value as NoteKind)} className="w-28">
          <option value="note">Note</option>
          <option value="issue">Issue</option>
        </Select>
        <Button type="submit" variant="secondary" loading={loading}>Post</Button>
      </form>
      <ErrorMessage message={error} />
    </div>
  );
}
