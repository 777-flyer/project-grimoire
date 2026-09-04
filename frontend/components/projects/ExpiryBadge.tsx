import { Badge } from "@/components/shared/Badge";

export function ExpiryBadge({ expiresOn }: { expiresOn: string | null }) {
  if (!expiresOn) return null;

  const days = Math.ceil((new Date(expiresOn).getTime() - Date.now()) / (1000 * 60 * 60 * 24));

  if (days < 0) {
    return <Badge tone="danger">expired {Math.abs(days)}d ago</Badge>;
  }
  if (days <= 30) {
    return <Badge tone="danger">expires in {days}d</Badge>;
  }
  if (days <= 90) {
    return <Badge tone="warning">expires in {days}d</Badge>;
  }
  return <Badge tone="neutral">expires {new Date(expiresOn).toLocaleDateString()}</Badge>;
}
