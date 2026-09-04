"use client";

import { ChevronRight, FolderKanban } from "lucide-react";
import Link from "next/link";

import { ProjectSummary } from "@/lib/types";

export function ProjectList({ projects }: { projects: ProjectSummary[] }) {
  if (projects.length === 0) {
    return (
      <div className="border border-dashed border-sand-300 rounded-xl p-10 text-center text-sm text-ink-400">
        No projects yet.
      </div>
    );
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {projects.map((project) => (
        <Link
          key={project.id}
          href={`/projects/${project.id}`}
          className="group bg-surface border border-sand-200 rounded-xl p-5 hover:border-accent-600/50 hover:shadow-sm transition-all duration-150 flex items-start gap-3"
        >
          <div className="w-10 h-10 rounded-lg bg-accent-100 text-accent-700 flex items-center justify-center shrink-0">
            <FolderKanban size={18} />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-ink-900 group-hover:text-accent-700 transition-colors truncate">
              {project.name}
            </h3>
            <p className="text-xs text-ink-400 mt-1">
              Created {new Date(project.created_at).toLocaleDateString()}
            </p>
          </div>
          <ChevronRight size={16} className="text-ink-300 group-hover:text-accent-600 transition-colors shrink-0 mt-2" />
        </Link>
      ))}
    </div>
  );
}
