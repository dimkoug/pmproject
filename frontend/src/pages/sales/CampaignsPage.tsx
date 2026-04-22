import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { useGetCampaignsQuery, useCreateCampaignMutation } from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";
import { promptForValues } from "../../shell/modalService";

type Campaign = {
  id: string;
  name: string;
  status: string;
  budget?: number;
  actual_cost?: number;
  start_date?: string;
  end_date?: string;
};

export default function CampaignsPage() {
  const { data: campaigns = [], isLoading, refetch } = useGetCampaignsQuery();
  const [createCampaign] = useCreateCampaignMutation();
  const { open: openPeek } = useDrawerPeek();

  const columns = useMemo<ColumnDef<Campaign, any>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Name",
        cell: (c) => <span style={{ fontWeight: 500 }}>{c.getValue() as string}</span>,
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: (c) => <span className="badge badge-blue">{c.getValue() as string}</span>,
      },
      {
        accessorKey: "budget",
        header: "Budget",
        cell: (c) => {
          const v = c.getValue() as number | undefined;
          return `$${v?.toLocaleString() ?? 0}`;
        },
      },
      {
        accessorKey: "actual_cost",
        header: "Actual",
        cell: (c) => {
          const v = c.getValue() as number | undefined;
          return `$${v?.toLocaleString() ?? 0}`;
        },
      },
      {
        id: "dates",
        header: "Dates",
        cell: (c) => {
          const r = c.row.original;
          return <span style={{ fontSize: "0.82rem" }}>{r.start_date || "-"} → {r.end_date || "-"}</span>;
        },
      },
    ],
    [],
  );

  return (
    <div>
      <PageHeader title="Campaigns" subtitle="Marketing programs with budget and spend tracking." />
      <CommandBar
        items={[
          {
            key: "new", label: "New campaign", variant: "primary",
            onClick: async () => {
              const v = await promptForValues({
                title: "New campaign",
                submitLabel: "Create",
                fields: [
                  { name: "name", label: "Campaign name", required: true },
                  { name: "budget", label: "Budget", kind: "number", step: 0.01 },
                ],
              });
              if (!v) return;
              const budget = parseFloat(v.budget || "0");
              await createCampaign({ name: v.name, budget, actual_cost: 0, status: "planned" });
              refetch();
            },
          },
        ]}
      />
      <DataTable
        columns={columns}
        data={campaigns as Campaign[]}
        isLoading={isLoading}
        emptyTitle="No campaigns yet"
        emptyDescription="Launch your first campaign to start tracking spend."
        onRowClick={(row) => openPeek("campaign", row.id)}
      />
    </div>
  );
}
