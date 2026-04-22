import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { useGetAccountsQuery, useCreateAccountMutation } from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";
import { promptForValues } from "../../shell/modalService";

const ACCOUNT_TYPES = ["asset", "liability", "equity", "revenue", "expense"];

type Account = {
  id: string;
  code: string;
  name: string;
  account_type: string;
  balance?: number;
};

export default function AccountsPage() {
  const { data: accounts = [], isLoading, refetch } = useGetAccountsQuery();
  const [createAccount] = useCreateAccountMutation();
  const { open: openPeek } = useDrawerPeek();

  const columns = useMemo<ColumnDef<Account, any>[]>(
    () => [
      {
        accessorKey: "code",
        header: "Code",
        cell: (c) => <span style={{ fontWeight: 600 }}>{c.getValue() as string}</span>,
      },
      { accessorKey: "name", header: "Name" },
      {
        accessorKey: "account_type",
        header: "Type",
        cell: (c) => <span className="badge badge-blue">{c.getValue() as string}</span>,
      },
      {
        accessorKey: "balance",
        header: "Balance",
        cell: (c) => {
          const v = c.getValue() as number | undefined;
          return `$${v?.toLocaleString() ?? 0}`;
        },
      },
    ],
    [],
  );

  return (
    <div>
      <PageHeader title="Chart of accounts" subtitle="General ledger accounts with running balances." />
      <CommandBar
        items={[
          {
            key: "new", label: "New account", variant: "primary",
            onClick: async () => {
              const v = await promptForValues({
                title: "New account",
                submitLabel: "Create",
                fields: [
                  { name: "code", label: "Code", placeholder: "e.g. 1000", required: true },
                  { name: "name", label: "Name", required: true },
                  {
                    name: "account_type", label: "Type", kind: "select", required: true, defaultValue: "asset",
                    options: ACCOUNT_TYPES.map((t) => ({ value: t, label: t })),
                  },
                ],
              });
              if (!v) return;
              await createAccount({ code: v.code, name: v.name, account_type: v.account_type || "asset" });
              refetch();
            },
          },
        ]}
      />
      <DataTable
        columns={columns}
        data={accounts as Account[]}
        isLoading={isLoading}
        emptyTitle="No accounts yet"
        emptyDescription="Create your chart of accounts to start posting journal entries."
        onRowClick={(row) => openPeek("account", row.id)}
      />
    </div>
  );
}
