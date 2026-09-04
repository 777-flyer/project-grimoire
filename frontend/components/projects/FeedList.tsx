import { Badge } from "@/components/shared/Badge";
import { FeedEvent, FeedEventType } from "@/lib/types";

const EVENT_TONE: Record<FeedEventType, "accent" | "success" | "warning" | "danger" | "neutral"> = {
  PROJECT_CREATED: "accent",
  MEMBER_ADDED: "accent",
  MEMBER_REVOKED: "danger",
  RECORD_REQUESTED: "warning",
  RECORD_APPROVED: "success",
  RECORD_REJECTED: "danger",
  RECORD_EDITED: "neutral",
  CHANGE_REQUESTED: "warning",
  CHANGE_APPROVED: "success",
  CHANGE_REJECTED: "danger",
  ISSUE_REPORTED: "danger",
  ISSUE_RESOLVED: "success",
  NOTE_ADDED: "neutral",
  KEY_ROTATED: "accent",
};

export function FeedList({ events }: { events: FeedEvent[] }) {
  if (events.length === 0) {
    return <p className="text-sm text-ink-400">No activity yet.</p>;
  }

  return (
    <ol className="flex flex-col gap-3">
      {events.map((event) => (
        <li key={event.id} className="flex gap-3 text-sm">
          <div className="w-2 h-2 rounded-full bg-sand-400 mt-1.5 shrink-0" />
          <div>
            <div className="flex items-center gap-2 mb-0.5">
              <Badge tone={EVENT_TONE[event.event_type]}>{event.event_type.replace(/_/g, " ").toLowerCase()}</Badge>
              <span className="text-xs text-ink-400">{new Date(event.created_at).toLocaleString()}</span>
            </div>
            <p className="text-ink-700">
              {event.actor_id !== null && <span className="font-medium text-ink-900">user #{event.actor_id} </span>}
              {event.message}
            </p>
          </div>
        </li>
      ))}
    </ol>
  );
}
