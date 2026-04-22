import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { useGetAssetsQuery, useCreateAssetMutation } from "../../services/api";
import { useProjectContext } from "../../shell/useProjectContext";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";
import { promptForValues } from "../../shell/modalService";

type Asset = {
  id: string;
  name: string;
  asset_tag?: string;
  category?: string;
  status: string;
  current_value?: number;
  location?: string;
};

export default function AssetsPage() {
  const projectId = useProjectContext();
  const { data: assets = [], isLoading, refetch } = useGetAssetsQuery(projectId);
  const [createAsset] = useCreateAssetMutation();
  const { open: openPeek } = useDrawerPeek();

  const columns = useMemo<ColumnDef<Asset, any>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Name",
        cell: (c) => <span style={{ fontWeight: 500 }}>{c.getValue() as string}</span>,
      },
      { accessorKey: "asset_tag", header: "Tag", cell: (c) => (c.getValue() as string) || "-" },
      { accessorKey: "category", header: "Category", cell: (c) => (c.getValue() as string) || "-" },
      {
        accessorKey: "status",
        header: "Status",
        cell: (c) => <span className="badge badge-blue">{c.getValue() as string}</span>,
      },
      {
        accessorKey: "current_value",
        header: "Value",
        cell: (c) => {
          const v = c.getValue() as number | undefined;
          return v ? `$${v.toLocaleString()}` : "-";
        },
      },
      { accessorKey: "location", header: "Location", cell: (c) => (c.getValue() as string) || "-" },
    ],
    [],
  );

  return (
    <div>
      <PageHeader title="Assets" subtitle="Physical and intangible assets with value tracking." />
      <CommandBar
        items={[
          {
            key: "new", label: "New asset", variant: "primary",
            onClick: async () => {
              const v = await promptForValues({
                title: "New asset",
                submitLabel: "Create",
                fields: [
                  { name: "name", label: "Asset name", required: true },
                ],
              });
              if (!v) return;
              await createAsset({ name: v.name, project_id: projectId });
              refetch();
            },
          },
        ]}
      />
      <DataTable
        columns={columns}
        data={assets as Asset[]}
        isLoading={isLoading}
        emptyTitle="No assets yet"
        emptyDescription="Register your first asset to start depreciation tracking."
        onRowClick={(row) => openPeek("asset", row.id)}
      />
    </div>
  );
}
