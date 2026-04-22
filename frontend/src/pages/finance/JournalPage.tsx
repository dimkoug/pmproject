import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import {
  useGetJournalQuery, useCreateJournalMutation, usePostJournalMutation, useGetAccountsQuery,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";
import { promptForValues } from "../../shell/modalService";

type JournalEntry = {
  id: string;
  entry_number: string;
  entry_date?: string;
  memo?: string;
  is_posted: boolean;
};

export default function JournalPage() {
  const { data: journal = [], isLoading, refetch } = useGetJournalQuery();
  const { data: accounts = [] } = useGetAccountsQuery();
  const [createEntry] = useCreateJournalMutation();
  const [postEntry] = usePostJournalMutation();
  const { open: openPeek } = useDrawerPeek();

  const columns = useMemo<ColumnDef<JournalEntry, any>[]>(
    () => [
      {
        accessorKey: "entry_number",
        header: "Entry #",
        cell: (c) => <span style={{ fontWeight: 500 }}>{c.getValue() as string}</span>,
      },
      {
        accessorKey: "entry_date",
        header: "Date",
        cell: (c) => (c.getValue() as string) || "-",
      },
      {
        accessorKey: "memo",
        header: "Memo",
        cell: (c) => <span style={{ fontSize: "0.82rem" }}>{(c.getValue() as string) || "-"}</span>,
      },
      {
        accessorKey: "is_posted",
        header: "Posted",
        cell: (c) =>
          c.getValue() ? (
            <span className="badge badge-green">Yes</span>
          ) : (
            <span className="badge badge-yellow">No</span>
          ),
      },
      {
        id: "actions",
        header: "Actions",
        enableSorting: false,
        cell: (c) => {
          const j = c.row.original;
          return !j.is_posted ? (
            <button
              className="btn btn-sm"
              onClick={async (e) => {
                e.stopPropagation();
                await postEntry(j.id);
                refetch();
              }}
            >
              Post
            </button>
          ) : null;
        },
      },
    ],
    [postEntry, refetch],
  );

  return (
    <div>
      <PageHeader title="Journal entries" subtitle="Manual double-entry bookkeeping." />
      <CommandBar
        items={[
          {
            key: "new", label: "New entry", variant: "primary",
            disabled: accounts.length < 2,
            title: accounts.length < 2 ? "Add at least 2 accounts first" : undefined,
            onClick: async () => {
              const v = await promptForValues({
                title: "New journal entry",
                submitLabel: "Create",
                fields: [
                  { name: "entry_number", label: "Entry #", placeholder: `J-${Date.now().toString().slice(-6)}` },
                  { name: "amount", label: "Amount", kind: "number", required: true, step: 0.01 },
                ],
              });
              if (!v) return;
              const entry_number = v.entry_number || `J-${Date.now().toString().slice(-6)}`;
              const amt = parseFloat(v.amount || "0");
              if (!amt) return;
              const [debit, credit] = [accounts[0], accounts[1]];
              await createEntry({
                entry_number, memo: "Manual",
                lines: [
                  { account_id: debit.id, debit: amt, credit: 0 },
                  { account_id: credit.id, debit: 0, credit: amt },
                ],
              });
              refetch();
            },
          },
        ]}
      />
      <DataTable
        columns={columns}
        data={journal as JournalEntry[]}
        isLoading={isLoading}
        emptyTitle="No journal entries yet"
        emptyDescription="Create your first manual entry to post to the ledger."
        onRowClick={(row) => openPeek("journal-entry", row.id)}
      />
    </div>
  );
}
