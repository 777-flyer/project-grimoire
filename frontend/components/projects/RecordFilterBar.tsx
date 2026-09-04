"use client";

import { Select } from "@/components/shared/Select";
import { ApprovalStatus, Environment, PlatformType } from "@/lib/types";

export interface RecordFilters {
  platform_type: PlatformType | "";
  environment: Environment | "";
  approval_status: ApprovalStatus | "";
}

export function RecordFilterBar({ filters, onChange }: { filters: RecordFilters; onChange: (filters: RecordFilters) => void }) {
  return (
    <div className="flex flex-wrap items-end gap-3">
      <Select
        id="filter-platform"
        label="Platform"
        value={filters.platform_type}
        onChange={(e) => onChange({ ...filters, platform_type: e.target.value as RecordFilters["platform_type"] })}
        className="w-40"
      >
        <option value="">All platforms</option>
        <option value="DOMAIN">Domain</option>
        <option value="HOSTING">Hosting</option>
        <option value="EMAIL">Email</option>
        <option value="OTHER">Other</option>
      </Select>
      <Select
        id="filter-environment"
        label="Environment"
        value={filters.environment}
        onChange={(e) => onChange({ ...filters, environment: e.target.value as RecordFilters["environment"] })}
        className="w-40"
      >
        <option value="">All environments</option>
        <option value="PRODUCTION">Production</option>
        <option value="STAGING">Staging</option>
        <option value="DEVELOPMENT">Development</option>
      </Select>
      <Select
        id="filter-status"
        label="Status"
        value={filters.approval_status}
        onChange={(e) => onChange({ ...filters, approval_status: e.target.value as RecordFilters["approval_status"] })}
        className="w-40"
      >
        <option value="">All statuses</option>
        <option value="PENDING">Pending</option>
        <option value="APPROVED">Approved</option>
        <option value="REJECTED">Rejected</option>
      </Select>
    </div>
  );
}
