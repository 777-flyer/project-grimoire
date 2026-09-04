"use client";

import { useEffect, useState } from "react";

import { CreateProjectForm } from "@/components/dashboard/CreateProjectForm";
import { ProjectList } from "@/components/dashboard/ProjectList";
import { TaskSummaryWidget } from "@/components/dashboard/TaskSummaryWidget";
import { useAuth } from "@/lib/AuthContext";
import { api } from "@/lib/api";
import { ProjectSummary } from "@/lib/types";

export default function DashboardPage() {
  const profile = useAuth();
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null);
  const canCreate = profile.role === "SUPER_ADMIN";

  useEffect(() => {
    api.get<ProjectSummary[]>("/api/vault/projects").then(setProjects).catch(() => {});
  }, []);

  return (
    <main className="max-w-5xl mx-auto px-6 py-10 flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-semibold text-ink-900">Welcome back, {profile.username}</h1>
        <p className="text-sm text-ink-500 mt-1">
          Every client engagement your team is running, in one vault.
        </p>
      </div>

      <TaskSummaryWidget />

      {canCreate && (
        <CreateProjectForm onCreated={(project) => setProjects((prev) => [project, ...(prev ?? [])])} />
      )}

      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-ink-400 mb-3">Projects</h2>
        {projects === null ? (
          <p className="text-sm text-ink-400">Loading...</p>
        ) : (
          <ProjectList projects={projects} />
        )}
      </div>
    </main>
  );
}
