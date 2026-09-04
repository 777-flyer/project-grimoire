"use client";

import { Activity, KeyRound, Users } from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { FeedList } from "@/components/projects/FeedList";
import { GrantAccessForm } from "@/components/projects/GrantAccessForm";
import { MembersList } from "@/components/projects/MembersList";
import { ProjectHeader } from "@/components/projects/ProjectHeader";
import { RecordFilterBar, RecordFilters } from "@/components/projects/RecordFilterBar";
import { RecordForm } from "@/components/projects/RecordForm";
import { RecordList } from "@/components/projects/RecordList";
import { RotateKeyButton } from "@/components/projects/RotateKeyButton";
import { Tabs } from "@/components/shared/Tabs";
import { useAuth } from "@/lib/AuthContext";
import { api } from "@/lib/api";
import { FeedEvent, ProjectDetail, RecordSummary } from "@/lib/types";

type TabKey = "records" | "feed" | "team";

export default function ProjectDetailPage() {
  const params = useParams<{ id: string }>();
  const projectId = Number(params.id);
  const profile = useAuth();

  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [records, setRecords] = useState<RecordSummary[] | null>(null);
  const [feed, setFeed] = useState<FeedEvent[] | null>(null);
  const [tab, setTab] = useState<TabKey>("records");
  const [filters, setFilters] = useState<RecordFilters>({ platform_type: "", environment: "", approval_status: "" });

  useEffect(() => {
    api.get<ProjectDetail>(`/api/vault/projects/${projectId}`).then(setProject).catch(() => {});
    api.get<RecordSummary[]>(`/api/vault/projects/${projectId}/records`).then(setRecords).catch(() => {});
  }, [projectId]);

  // Refetch the feed each time the tab opens, since actions elsewhere on this page change it.
  useEffect(() => {
    if (tab === "feed") {
      api.get<FeedEvent[]>(`/api/vault/projects/${projectId}/feed`).then(setFeed).catch(() => {});
    }
  }, [tab, projectId]);

  if (!project || !records) {
    return <main className="max-w-5xl mx-auto px-6 py-10 text-sm text-ink-400">Loading...</main>;
  }

  const pendingCount = records.filter((r) => r.approval_status === "PENDING").length;
  const canCreateRecord = profile.role === "SUPER_ADMIN" || profile.role === "PROJECT_MANAGER" || profile.role === "DEVOPS_ENGINEER";
  const filteredRecords = records.filter((r) =>
    (!filters.platform_type || r.platform_type === filters.platform_type) &&
    (!filters.environment || r.environment === filters.environment) &&
    (!filters.approval_status || r.approval_status === filters.approval_status)
  );

  return (
    <main className="max-w-5xl mx-auto px-6 py-10 flex flex-col gap-6">
      <ProjectHeader project={project} />

      <Tabs
        active={tab}
        onChange={(key) => setTab(key as TabKey)}
        tabs={[
          { key: "records", label: "Credentials", icon: KeyRound, count: pendingCount },
          { key: "feed", label: "Activity", icon: Activity },
          { key: "team", label: "Team", icon: Users },
        ]}
      />

      {tab === "records" && (
        <div className="flex flex-col gap-4">
          {canCreateRecord && (
            <RecordForm projectId={projectId} onCreated={(record) => setRecords((prev) => [record, ...(prev ?? [])])} />
          )}
          {records.length > 0 && <RecordFilterBar filters={filters} onChange={setFilters} />}
          <RecordList
            projectId={projectId}
            records={filteredRecords}
            canManage={project.can_manage}
            onUpdated={(updated) => setRecords((prev) => (prev ?? []).map((r) => (r.id === updated.id ? updated : r)))}
          />
        </div>
      )}

      {tab === "feed" && (
        <div className="bg-surface border border-sand-200 rounded-xl p-5">
          {feed === null ? <p className="text-sm text-ink-400">Loading...</p> : <FeedList events={feed} />}
        </div>
      )}

      {tab === "team" && (
        <div className="flex flex-col gap-6">
          {project.can_manage && (
            <>
              <GrantAccessForm
                projectId={projectId}
                onGranted={(userId, role) =>
                  setProject((p) => (p ? { ...p, members: [...p.members, { user_id: userId, role, granted_at: new Date().toISOString() }] } : p))
                }
              />
              <RotateKeyButton projectId={projectId} />
            </>
          )}
          <MembersList
            projectId={projectId}
            members={project.members}
            canManage={project.can_manage}
            onRevoked={(userId) =>
              setProject((p) => (p ? { ...p, members: p.members.filter((m) => m.user_id !== userId) } : p))
            }
          />
        </div>
      )}
    </main>
  );
}
