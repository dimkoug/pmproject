import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import {
  useGetRetentionPoliciesQuery, useCreateRetentionPolicyMutation, useApplyRetentionMutation,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";
import { promptForValues, notifyUser } from "../../shell/modalService";

type Policy = {
  id: string;
  name: string;
  tag_match?: string;
  folder_id?: string;
  days_after: number;
  action: string;
  is_active: boolean;
};

export default function RetentionPage() {
  const { data: policies = [], isLoading, refetch } = useGetRetentionPoliciesQuery();
  const [createPolicy] = useCreateRetentionPolicyMutation();
  const [applyRetention] = useApplyRetentionMutation();
  const { open: openPeek } = useDrawerPeek();

  const columns = useMemo<ColumnDef<Policy, any>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Name",
        cell: (c) => <span style={{ fontWeight: 500 }}>{c.getValue() as string}</span>,
      },
      {
        id: "match",
        header: "Folder / Tag",
        cell: (c) => {
          const p = c.row.original;
          return (
            <span style={{ fontSize: "0.82rem" }}>
              {p.tag_match ? `tag: ${p.tag_match}` : p.folder_id ? "folder" : "all"}
            </span>
          );
        },
      },
      { accessorKey: "days_after", header: "Days" },
      {
        accessorKey: "action",
        header: "Action",
        cell: (c) => <span className="badge badge-blue">{c.getValue() as string}</span>,
      },
      {
        accessorKey: "is_active",
        header: "Active",
        cell: (c) =>
          c.getValue() ? (
            <span className="badge badge-green">Yes</span>
          ) : (
            <span className="badge badge-gray">No</span>
          ),
      },
    ],
    [],
  );

  return (
    <div>
      <PageHeader title="Retention policies" subtitle="Archive or delete documents after a configurable age." />
      <CommandBar
        items={[
          {
            key: "apply", label: "Apply now",
            onClick: async () => {
              const r: any = await applyRetention();
              await notifyUser({ title: "Retention applied", description: `Archived ${r.data?.archived || 0}, deleted ${r.data?.deleted || 0}` });
              refetch();
            },
          },
          {
            key: "new", label: "New policy", variant: "primary",
            onClick: async () => {
              const v = await promptForValues({
                title: "New retention policy",
                submitLabel: "Create",
                fields: [
                  { name: "name", label: "Policy name", required: true },
                  { name: "days_after", label: "Days after last update", kind: "number", required: true, min: 1 },
                  {
                    name: "action", label: "Action", kind: "select", required: true, defaultValue: "archive",
                    options: [
                      { value: "archive", label: "Archive" },
                      { value: "delete", label: "Delete" },
                    ],
                  },
                ],
              });
              if (!v) return;
              const days = parseInt(v.days_after || "0");
              if (!days) return;
              await createPolicy({ name: v.name, days_after: days, action: v.action || "archive" });
              refetch();
            },
          },
        ]}
      />
      <DataTable
        columns={columns}
        data={policies as Policy[]}
        isLoading={isLoading}
        emptyTitle="No retention policies yet"
        emptyDescription="Add a policy to archive or delete aged documents automatically."
        onRowClick={(row) => openPeek("retention-policy", row.id)}
      />
    </div>
  );
}
