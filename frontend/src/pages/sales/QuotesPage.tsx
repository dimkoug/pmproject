import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { useGetQuotesQuery, useCreateQuoteMutation, useConvertQuoteMutation } from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";
import { promptForValues } from "../../shell/modalService";

type Quote = {
  id: string;
  quote_number: string;
  status: string;
  total?: number;
  valid_until?: string;
  invoice_id?: string;
};

export default function QuotesPage() {
  const { data: quotes = [], isLoading, refetch } = useGetQuotesQuery();
  const [createQuote] = useCreateQuoteMutation();
  const [convertQuote] = useConvertQuoteMutation();
  const { open: openPeek } = useDrawerPeek();

  const columns = useMemo<ColumnDef<Quote, any>[]>(
    () => [
      {
        accessorKey: "quote_number",
        header: "Number",
        cell: (c) => <span style={{ fontWeight: 500 }}>{c.getValue() as string}</span>,
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: (c) => <span className="badge badge-blue">{c.getValue() as string}</span>,
      },
      {
        accessorKey: "total",
        header: "Total",
        cell: (c) => {
          const v = c.getValue() as number | undefined;
          return <span style={{ fontWeight: 600 }}>${v?.toLocaleString()}</span>;
        },
      },
      {
        accessorKey: "valid_until",
        header: "Valid",
        cell: (c) => (c.getValue() as string) || "-",
      },
      {
        id: "actions",
        header: "Actions",
        enableSorting: false,
        cell: (c) => {
          const q = c.row.original;
          return !q.invoice_id ? (
            <button
              className="btn btn-sm"
              onClick={async (e) => {
                e.stopPropagation();
                await convertQuote(q.id);
                refetch();
              }}
            >Convert to invoice</button>
          ) : (
            <span className="badge badge-green">Converted</span>
          );
        },
      },
    ],
    [convertQuote, refetch],
  );

  return (
    <div>
      <PageHeader title="Quotes" subtitle="Proposals that convert into invoices on acceptance." />
      <CommandBar
        items={[
          {
            key: "new", label: "New quote", variant: "primary",
            onClick: async () => {
              const v = await promptForValues({
                title: "New quote",
                submitLabel: "Create",
                fields: [
                  { name: "quote_number", label: "Quote number", placeholder: `Q-${Date.now().toString().slice(-6)}` },
                  { name: "description", label: "Line item description", required: true },
                  { name: "unit_price", label: "Unit price", kind: "number", step: 0.01, defaultValue: "0" },
                ],
              });
              if (!v) return;
              const num = v.quote_number || `Q-${Date.now().toString().slice(-6)}`;
              const price = parseFloat(v.unit_price || "0");
              await createQuote({
                quote_number: num,
                items: [{ description: v.description, quantity: 1, unit_price: price }],
              });
              refetch();
            },
          },
        ]}
      />
      <DataTable
        columns={columns}
        data={quotes as Quote[]}
        isLoading={isLoading}
        emptyTitle="No quotes yet"
        emptyDescription="Create your first quote to send a proposal."
        onRowClick={(row) => openPeek("quote", row.id)}
      />
    </div>
  );
}
