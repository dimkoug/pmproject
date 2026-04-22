import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import {
  useGetDepreciationQuery, useCreateDepreciationMutation, useRunDepreciationMutation,
  useGetAssetsQuery,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";
import { promptForValues, notifyUser } from "../../shell/modalService";

type Depreciation = {
  id: string;
  asset_id: string;
  method: string;
  useful_life_months: number;
  salvage_value: number;
  accumulated?: number;
  last_run?: string;
};

export default function DepreciationPage() {
  const { data: dep = [], isLoading, refetch } = useGetDepreciationQuery();
  const { data: assets = [] } = useGetAssetsQuery();
  const [createDep] = useCreateDepreciationMutation();
  const [runDep] = useRunDepreciationMutation();
  const { open: openPeek } = useDrawerPeek();

  const columns = useMemo<ColumnDef<Depreciation, any>[]>(
    () => [
      {
        accessorKey: "asset_id",
        header: "Asset",
        cell: (c) => <span style={{ fontSize: "0.75rem" }}>{(c.getValue() as string).slice(0, 8)}…</span>,
      },
      {
        accessorKey: "method",
        header: "Method",
        cell: (c) => <span className="badge badge-blue">{c.getValue() as string}</span>,
      },
      { accessorKey: "useful_life_months", header: "Life (mo)" },
      { accessorKey: "salvage_value", header: "Salvage", cell: (c) => `$${c.getValue()}` },
      {
        accessorKey: "accumulated",
        header: "Accumulated",
        cell: (c) => {
          const v = c.getValue() as number | undefined;
          return <span style={{ fontWeight: 600 }}>${v?.toLocaleString()}</span>;
        },
      },
      {
        accessorKey: "last_run",
        header: "Last run",
        cell: (c) => <span style={{ fontSize: "0.82rem" }}>{(c.getValue() as string) || "—"}</span>,
      },
    ],
    [],
  );

  return (
    <div>
      <PageHeader title="Depreciation schedules" subtitle="Asset depreciation runs posted to the journal." />
      <CommandBar
        items={[
          {
            key: "run", label: "Run now",
            onClick: async () => {
              const r: any = await runDep();
              await notifyUser({
                title: "Depreciation run complete",
                description: `Posted ${r.data?.schedules_posted || 0} / $${r.data?.total_depreciation || 0}`,
              });
              refetch();
            },
          },
          {
            key: "new", label: "New schedule", variant: "primary",
            disabled: !assets.length,
            onClick: async () => {
              const v = await promptForValues({
                title: "New depreciation schedule",
                submitLabel: "Create",
                fields: [
                  { name: "asset_id", label: "Asset ID", defaultValue: assets[0]?.id || "" },
                  { name: "useful_life_months", label: "Useful life (months)", kind: "number", defaultValue: "60", min: 1 },
                  { name: "salvage_value", label: "Salvage value", kind: "number", step: 0.01, defaultValue: "0" },
                  { name: "start_date", label: "Start date", kind: "date", defaultValue: new Date().toISOString().slice(0, 10) },
                ],
              });
              if (!v) return;
              const asset_id = v.asset_id || assets[0]?.id;
              const useful_life_months = parseInt(v.useful_life_months || "60");
              const salvage_value = parseFloat(v.salvage_value || "0");
              const start_date = v.start_date || "";
              await createDep({ asset_id, useful_life_months, salvage_value, start_date });
              refetch();
            },
          },
        ]}
      />
      <DataTable
        columns={columns}
        data={dep as Depreciation[]}
        isLoading={isLoading}
        emptyTitle="No schedules yet"
        emptyDescription="Create a depreciation schedule to amortize an asset over its useful life."
        onRowClick={(row) => openPeek("depreciation", row.id)}
      />
    </div>
  );
}
