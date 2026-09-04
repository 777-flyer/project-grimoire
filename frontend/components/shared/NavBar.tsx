"use client";

import { FolderKanban, LogOut, ShieldCheck, UserCircle } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";

import { api } from "@/lib/api";
import { useToast } from "@/lib/ToastContext";
import { Role } from "@/lib/types";

const ROLE_LABELS: Record<Role, string> = {
  SUPER_ADMIN: "Super Admin",
  PROJECT_MANAGER: "Project Manager",
  DEVOPS_ENGINEER: "DevOps Engineer",
  BACKEND_DEVELOPER: "Backend Developer",
};

function NavLink({ href, active, children }: { href: string; active: boolean; children: ReactNode }) {
  return (
    <Link
      href={href}
      className={`flex items-center gap-1.5 transition-colors ${active ? "text-accent-700 font-medium" : "text-ink-500 hover:text-ink-900"}`}
    >
      {children}
    </Link>
  );
}

export function NavBar({ role, username }: { role?: Role; username?: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const { toast } = useToast();

  async function handleLogout() {
    try {
      await api.post("/api/auth/logout");
      toast("You've been logged out.", "info");
    } finally {
      router.push("/login");
    }
  }

  return (
    <nav className="border-b border-sand-200 bg-surface-raised px-6 py-4 flex items-center justify-between">
      <Link href="/dashboard" className="flex items-center gap-2">
        <span className="w-6 h-6 rounded-md bg-accent-600 flex items-center justify-center text-sand-50 text-sm font-bold">
          G
        </span>
        <span className="text-lg font-semibold tracking-tight text-ink-900">Grimoire</span>
      </Link>
      <div className="flex items-center gap-6 text-sm">
        <NavLink href="/dashboard" active={pathname === "/dashboard"}>
          <FolderKanban size={16} /> Projects
        </NavLink>
        {role === "SUPER_ADMIN" && (
          <NavLink href="/admin" active={pathname === "/admin"}>
            <ShieldCheck size={16} /> Admin
          </NavLink>
        )}
        <NavLink href="/profile" active={pathname === "/profile"}>
          <UserCircle size={16} /> Profile
        </NavLink>
        {role && (
          <span className="hidden lg:inline text-ink-400 border-l border-sand-200 pl-6">
            {username} &middot; {ROLE_LABELS[role]}
          </span>
        )}
        <button onClick={handleLogout} className="flex items-center gap-1.5 text-ink-500 hover:text-ink-900 transition-colors">
          <LogOut size={16} /> Log out
        </button>
      </div>
    </nav>
  );
}
