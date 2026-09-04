import { ReactNode } from "react";

import { AuthGuard } from "@/components/shared/AuthGuard";

export const dynamic = "force-dynamic";

export default function AppLayout({ children }: { children: ReactNode }) {
  return <AuthGuard>{children}</AuthGuard>;
}
