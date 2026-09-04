import { Badge } from "@/components/shared/Badge";
import { PasswordRotationStatus } from "@/lib/types";

export function PasswordRotationBadge({ rotation }: { rotation: PasswordRotationStatus }) {
  if (rotation.days_since_rotation === null) {
    return <Badge tone="warning">password age unknown</Badge>;
  }
  return <Badge tone={rotation.tone}>password {rotation.days_since_rotation}d old</Badge>;
}
