import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import {
  useGetRequisitionsQuery, useCreateRequisitionMutation,
  useUpdateRequisitionStatusMutation, useConvertRequisitionMutation,
  useGetVendorsQuery,
} from "../../services/api";
import { useProjectContext } from "../../shell/useProjectContext";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";
import { promptForValues } from "../../shell/modalService";

const REQ_STATUSES = ["draft", "submitted", "approved", "rejected", "converted"];

type Requisition = {
  id: string;
  req_number: string;
  status: string;
  estimated_amount?: number;
  needed_by?: string;
  converted_po_id?: string;
};

export default function RequisitionsPage() {
  const projectId = useProjectContext();
  const { data: reqs = [], isLoading, refetch } = useGetRequisitionsQuery();
  const { data: vendors = [] } = useGetVendorsQuery();
  const [createReq] = useCreateRequisitionMutation();
  const [updateStatus] = useUpdateRequisitionStatusMutation();
  const [convert] = useConvertRequisitionMutation();
  const { open: openPeek } = useDrawerPeek();

  const columns = useMemo<ColumnDef<Requisition, any>[]>(
    () => [
      {
        accessorKey: "req_number",
        header: "Number",
        cell: (c) => <span style={{ fontWeight: 500 }}>{c.getValue() as string}</span>,
      },
      {
        accessorKey: "status",
        header: "Status",
        enableSorting: false,
        cell: (c) => {
          const r = c.row.original;
          return (
            <select
              value={r.status}
              onClick={(e) => e.stopPropagation()}
              onChange={(e) => { updateStatus({ id: r.id, status: e.target.value }); refetch(); }}
              style={{ fontSize: "0.8rem", padding: "0.2rem" }}
            >
              {REQ_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          );
        },
      },
      {
        accessorKey: "estimated_amount",
        header: "Amount",
        cell: (c) => {
          const v = c.getValue() as number | undefined;
          return <span style={{ fontWeight: 600 }}>${v?.toLocaleString()}</span>;
        },
      },
      {
        accessorKey: "needed_by",
        header: "Needed by",
        cell: (c) => (c.getValue() as string) || "-",
      },
      {
        id: "actions",
        header: "Actions",
        enableSorting: false,
        cell: (c) => {
          const r = c.row.original;
          if (r.status === "approved" && !r.converted_po_id && vendors.length > 0) {
            return (
              <button
                className="btn btn-sm"
                onClick={async (e) => {
                  e.stopPropagation();
                  await convert({ id: r.id, body: { vendor_id: vendors[0].id } });
                  refetch();
                }}
              >
                → PO
              </button>
            );
          }
          if (r.converted_po_id) {
            return <span className="badge badge-green">Converted</span>;
          }
          return null;
        },
      },
    ],
    [updateStatus, convert, refetch, vendors],
  );

  return (
    <div>
      <PageHeader title="Purchase requisitions" subtitle="Internal requests that convert to POs once approved." />
      <CommandBar
        items={[
          {
            key: "new", label: "New requisition", variant: "primary",
            onClick: async () => {
              const v = await promptForValues({
                title: "New requisition",
                submitLabel: "Create",
                fields: [
                  { name: "req_number", label: "Requisition #", placeholder: `REQ-${Date.now().toString().slice(-6)}` },
                  { name: "description", label: "Item description", required: true },
                  { name: "quantity", label: "Quantity", kind: "number", defaultValue: "1", step: 0.01 },
                  { name: "unit_price", label: "Unit price", kind: "number", defaultValue: "0", step: 0.01 },
                  { name: "justification", label: "Justification", kind: "textarea" },
                ],
              });
              if (!v) return;
              const req_number = v.req_number || `REQ-${Date.now().toString().slice(-6)}`;
              const quantity = parseFloat(v.quantity || "1");
              const unit_price = parseFloat(v.unit_price || "0");
              await createReq({
                project_id: projectId,
                req_number,
                justification: v.justification || "",
                items: [{ description: v.description, quantity, unit_price }],
              });
              refetch();
            },
          },
        ]}
      />
      <DataTable
        columns={columns}
        data={reqs as Requisition[]}
        isLoading={isLoading}
        emptyTitle="No requisitions yet"
        emptyDescription="Create a requisition to request approval before cutting a PO."
        onRowClick={(row) => openPeek("requisition", row.id)}
      />
    </div>
  );
}
