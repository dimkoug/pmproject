import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import {
  useGetTerritoriesQuery, useCreateTerritoryMutation, useAutoAssignLeadsMutation,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";
import { promptForValues, notifyUser } from "../../shell/modalService";

type Territory = {
  id: string;
  name: string;
  rule_region?: string;
  rule_industry?: string;
  rule_min_revenue?: number;
  owner_id?: string;
};

export default function TerritoriesPage() {
  const { data: territories = [], isLoading, refetch } = useGetTerritoriesQuery();
  const [createTerritory] = useCreateTerritoryMutation();
  const [autoAssign] = useAutoAssignLeadsMutation();
  const { open: openPeek } = useDrawerPeek();

  const columns = useMemo<ColumnDef<Territory, any>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Name",
        cell: (c) => <span style={{ fontWeight: 500 }}>{c.getValue() as string}</span>,
      },
      {
        accessorKey: "rule_region",
        header: "Region",
        cell: (c) => (c.getValue() as string) || "-",
      },
      {
        accessorKey: "rule_industry",
        header: "Industry",
        cell: (c) => (c.getValue() as string) || "-",
      },
      {
        accessorKey: "rule_min_revenue",
        header: "Min revenue",
        cell: (c) => {
          const v = c.getValue() as number | undefined;
          return v ? `$${v.toLocaleString()}` : "-";
        },
      },
      {
        accessorKey: "owner_id",
        header: "Owner",
        cell: (c) => {
          const v = c.getValue() as string | undefined;
          return <span style={{ fontSize: "0.75rem" }}>{v ? `${v.slice(0, 8)}…` : "-"}</span>;
        },
      },
    ],
    [],
  );

  return (
    <div>
      <PageHeader title="Territories" subtitle="Rule-based lead routing (industry, region, revenue)." />
      <CommandBar
        items={[
          {
            key: "auto", label: "Auto-assign leads",
            onClick: async () => {
              const r: any = await autoAssign();
              await notifyUser({ title: "Auto-assign complete", description: `Assigned ${r.data?.assigned || 0} leads` });
            },
          },
          {
            key: "new", label: "New territory", variant: "primary",
            onClick: async () => {
              const v = await promptForValues({
                title: "New territory",
                submitLabel: "Create",
                fields: [
                  { name: "name", label: "Territory name", required: true },
                  { name: "industry", label: "Match industry", placeholder: "Optional" },
                  { name: "min_revenue", label: "Min revenue", kind: "number", step: 0.01, placeholder: "Optional" },
                ],
              });
              if (!v) return;
              const minRev = parseFloat(v.min_revenue || "0");
              await createTerritory({
                name: v.name,
                rule_industry: v.industry || undefined,
                rule_min_revenue: minRev || undefined,
              });
              refetch();
            },
          },
        ]}
      />
      <DataTable
        columns={columns}
        data={territories as Territory[]}
        isLoading={isLoading}
        emptyTitle="No territories yet"
        emptyDescription="Define your first territory to auto-route incoming leads."
        onRowClick={(row) => openPeek("territory", row.id)}
      />
    </div>
  );
}
