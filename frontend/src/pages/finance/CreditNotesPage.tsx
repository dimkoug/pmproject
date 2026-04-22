import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { useGetCreditNotesQuery, useCreateCreditNoteMutation } from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";
import { promptForValues } from "../../shell/modalService";

type CreditNote = {
  id: string;
  cn_number: string;
  invoice_id: string;
  amount?: number;
  reason?: string;
  issued_date: string;
};

export default function CreditNotesPage() {
  const { data: creditNotes = [], isLoading, refetch } = useGetCreditNotesQuery();
  const [createCN] = useCreateCreditNoteMutation();
  const { open: openPeek } = useDrawerPeek();

  const columns = useMemo<ColumnDef<CreditNote, any>[]>(
    () => [
      {
        accessorKey: "cn_number",
        header: "CN number",
        cell: (c) => <span style={{ fontWeight: 500 }}>{c.getValue() as string}</span>,
      },
      {
        accessorKey: "invoice_id",
        header: "Invoice",
        cell: (c) => <span style={{ fontSize: "0.75rem" }}>{(c.getValue() as string).slice(0, 8)}…</span>,
      },
      {
        accessorKey: "amount",
        header: "Amount",
        cell: (c) => {
          const v = c.getValue() as number | undefined;
          return `$${v?.toLocaleString() ?? 0}`;
        },
      },
      {
        accessorKey: "reason",
        header: "Reason",
        cell: (c) => <span style={{ fontSize: "0.82rem" }}>{(c.getValue() as string) || "-"}</span>,
      },
      { accessorKey: "issued_date", header: "Date" },
    ],
    [],
  );

  return (
    <div>
      <PageHeader title="Credit notes" subtitle="Adjustments issued against invoices." />
      <CommandBar
        items={[
          {
            key: "new", label: "New credit note", variant: "primary",
            onClick: async () => {
              const v = await promptForValues({
                title: "New credit note",
                submitLabel: "Create",
                fields: [
                  { name: "invoice_id", label: "Invoice ID", required: true },
                  { name: "cn_number", label: "CN number", placeholder: `CN-${Date.now().toString().slice(-6)}` },
                  { name: "amount", label: "Amount", kind: "number", required: true, step: 0.01 },
                  { name: "reason", label: "Reason", kind: "textarea" },
                ],
              });
              if (!v) return;
              const amount = parseFloat(v.amount || "0");
              await createCN({
                invoice_id: v.invoice_id,
                cn_number: v.cn_number || `CN-${Date.now().toString().slice(-6)}`,
                amount,
                reason: v.reason || "",
              });
              refetch();
            },
          },
        ]}
      />
      <DataTable
        columns={columns}
        data={creditNotes as CreditNote[]}
        isLoading={isLoading}
        emptyTitle="No credit notes yet"
        emptyDescription="Issue a credit note to adjust an invoice amount."
        onRowClick={(row) => openPeek("credit-note", row.id)}
      />
    </div>
  );
}
