import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import {
  useGetBankTransactionsQuery, useCreateBankTransactionMutation, useAutoMatchBankMutation,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";
import { promptForValues, notifyUser } from "../../shell/modalService";

type BankTxn = {
  id: string;
  txn_date?: string;
  description: string;
  amount: number;
  is_reconciled: boolean;
  matched_invoice_id?: string;
};

export default function BankPage() {
  const { data: bank = [], isLoading, refetch } = useGetBankTransactionsQuery();
  const [createBank] = useCreateBankTransactionMutation();
  const [autoMatch] = useAutoMatchBankMutation();
  const { open: openPeek } = useDrawerPeek();

  const columns = useMemo<ColumnDef<BankTxn, any>[]>(
    () => [
      {
        accessorKey: "txn_date",
        header: "Date",
        cell: (c) => (c.getValue() as string) || "-",
      },
      { accessorKey: "description", header: "Description" },
      {
        accessorKey: "amount",
        header: "Amount",
        cell: (c) => {
          const v = c.getValue() as number;
          return (
            <span style={{ fontWeight: 600, color: v >= 0 ? "var(--success)" : "var(--danger)" }}>
              ${v?.toLocaleString()}
            </span>
          );
        },
      },
      {
        accessorKey: "is_reconciled",
        header: "Reconciled",
        cell: (c) =>
          c.getValue() ? (
            <span className="badge badge-green">Yes</span>
          ) : (
            <span className="badge badge-gray">No</span>
          ),
      },
      {
        accessorKey: "matched_invoice_id",
        header: "Matched invoice",
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
      <PageHeader title="Bank transactions" subtitle="Ingest bank activity and auto-match against invoices." />
      <CommandBar
        items={[
          {
            key: "auto", label: "Auto match",
            onClick: async () => {
              const r: any = await autoMatch();
              await notifyUser({ title: "Auto-match complete", description: `Matched ${r.data?.matched || 0}` });
              refetch();
            },
          },
          {
            key: "new", label: "New transaction", variant: "primary",
            onClick: async () => {
              const v = await promptForValues({
                title: "New bank transaction",
                submitLabel: "Create",
                fields: [
                  { name: "description", label: "Description", required: true },
                  { name: "amount", label: "Amount", kind: "number", required: true, step: 0.01, helperText: "Negative for debit" },
                ],
              });
              if (!v) return;
              const amount = parseFloat(v.amount || "0");
              await createBank({ description: v.description, amount });
              refetch();
            },
          },
        ]}
      />
      <DataTable
        columns={columns}
        data={bank as BankTxn[]}
        isLoading={isLoading}
        emptyTitle="No bank transactions yet"
        emptyDescription="Import or log transactions to reconcile against invoices."
        onRowClick={(row) => openPeek("bank-txn", row.id)}
      />
    </div>
  );
}
