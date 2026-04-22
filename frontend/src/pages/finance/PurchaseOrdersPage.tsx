import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { useGetPurchaseOrdersQuery, useCreatePurchaseOrderMutation, useGetVendorsQuery } from "../../services/api";
import { useProjectContext } from "../../shell/useProjectContext";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";
import { promptForValues } from "../../shell/modalService";

type PO = {
  id: string;
  po_number: string;
  status: string;
  total_amount?: number;
  description?: string;
};

export default function PurchaseOrdersPage() {
  const projectId = useProjectContext();
  const { data: pos = [], isLoading, refetch } = useGetPurchaseOrdersQuery(projectId);
  const { data: vendors = [] } = useGetVendorsQuery();
  const [createPO] = useCreatePurchaseOrderMutation();
  const { open: openPeek } = useDrawerPeek();

  const columns = useMemo<ColumnDef<PO, any>[]>(
    () => [
      {
        accessorKey: "po_number",
        header: "PO number",
        cell: (c) => <span style={{ fontWeight: 500 }}>{c.getValue() as string}</span>,
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: (c) => <span className="badge badge-blue">{c.getValue() as string}</span>,
      },
      {
        accessorKey: "total_amount",
        header: "Amount",
        cell: (c) => {
          const v = c.getValue() as number | undefined;
          return `$${v?.toLocaleString() ?? 0}`;
        },
      },
      {
        accessorKey: "description",
        header: "Description",
        cell: (c) => (c.getValue() as string) || "-",
      },
    ],
    [],
  );

  return (
    <div>
      <PageHeader title="Purchase orders" subtitle="Orders placed with vendors." />
      <CommandBar
        items={[
          {
            key: "new", label: "New PO", variant: "primary",
            disabled: vendors.length === 0,
            onClick: async () => {
              const v = await promptForValues({
                title: "New purchase order",
                submitLabel: "Create",
                fields: [
                  { name: "po_number", label: "PO number", placeholder: `PO-${Date.now().toString().slice(-6)}` },
                  { name: "total_amount", label: "Total amount", kind: "number", required: true, step: 0.01 },
                  { name: "description", label: "Description", kind: "textarea" },
                ],
              });
              if (!v) return;
              const po_number = v.po_number || `PO-${Date.now().toString().slice(-6)}`;
              const total_amount = parseFloat(v.total_amount || "0");
              await createPO({
                po_number,
                total_amount,
                description: v.description || "",
                vendor_id: vendors[0].id,
                project_id: projectId,
              });
              refetch();
            },
          },
        ]}
      />
      <DataTable
        columns={columns}
        data={pos as PO[]}
        isLoading={isLoading}
        emptyTitle="No purchase orders yet"
        emptyDescription="Create your first PO to start tracking committed spend."
        onRowClick={(row) => openPeek("purchase-order", row.id)}
      />
    </div>
  );
}
