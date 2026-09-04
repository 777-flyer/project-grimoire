import { Badge } from "@/components/shared/Badge";
import { AdminUser, Role } from "@/lib/types";

const ROLE_TONE: Record<Role, "accent" | "success" | "neutral" | "warning"> = {
  SUPER_ADMIN: "accent",
  PROJECT_MANAGER: "success",
  DEVOPS_ENGINEER: "neutral",
  BACKEND_DEVELOPER: "warning",
};

export function UserList({ users }: { users: AdminUser[] }) {
  return (
    <div className="overflow-x-auto border border-sand-200 rounded-xl bg-surface">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-sand-200 text-left text-ink-400">
            <th className="px-4 py-3 font-medium">Username</th>
            <th className="px-4 py-3 font-medium">Email</th>
            <th className="px-4 py-3 font-medium">Role</th>
            <th className="px-4 py-3 font-medium">2FA</th>
            <th className="px-4 py-3 font-medium">Created</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr key={user.id} className="border-b border-sand-100 last:border-0">
              <td className="px-4 py-3 text-ink-900 font-medium">{user.username}</td>
              <td className="px-4 py-3 text-ink-700">{user.email}</td>
              <td className="px-4 py-3"><Badge tone={ROLE_TONE[user.role]}>{user.role.replace("_", " ")}</Badge></td>
              <td className="px-4 py-3">
                <Badge tone={user.totp_confirmed ? "success" : "warning"}>
                  {user.totp_confirmed ? "confirmed" : "pending"}
                </Badge>
              </td>
              <td className="px-4 py-3 text-ink-400">{new Date(user.created_at).toLocaleDateString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
