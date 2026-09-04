"use client";

import { RecordCard } from "@/components/projects/RecordCard";
import { RecordSummary } from "@/lib/types";

interface Props {
  projectId: number;
  records: RecordSummary[];
  canManage: boolean;
  onUpdated: (record: RecordSummary) => void;
}

export function RecordList({ projectId, records, canManage, onUpdated }: Props) {
  if (records.length === 0) {
    return (
      <div className="border border-dashed border-sand-300 rounded-xl p-10 text-center text-sm text-ink-400">
        No credentials purchased yet for this project.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {records.map((record) => (
        <RecordCard key={record.id} projectId={projectId} record={record} canManage={canManage} onUpdated={onUpdated} />
      ))}
    </div>
  );
}
