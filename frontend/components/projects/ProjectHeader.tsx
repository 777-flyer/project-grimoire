import { ProjectDetail } from "@/lib/types";

export function ProjectHeader({ project }: { project: ProjectDetail }) {
  return (
    <div>
      <h1 className="text-2xl font-semibold text-ink-900">{project.name}</h1>
      <p className="text-sm text-ink-500 mt-1">
        Managed by user #{project.manager} &middot; {project.members.length} member{project.members.length === 1 ? "" : "s"}
      </p>
    </div>
  );
}
