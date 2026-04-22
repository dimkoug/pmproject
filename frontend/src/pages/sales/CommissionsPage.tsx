import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import {
  useGetCommissionRulesQuery, useCreateCommissionRuleMutation, useComputeCommissionsMutation,
  useGetCommissionsQuery, usePayCommissionMutation,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";
import { promptForValues, notifyUser } from "../../shell/modalService";

type Rule = {
  id: string;
  name: string;
  percentage: number;
  min_amount: number;
  max_amount?: number;
  is_active: boolean;
};

type Commission = {
  id: string;
  user_id: string;
  base_amount?: number;
  commission?: number;
  paid: boolean;
};

export default function CommissionsPage() {
  const { data: rules = [], isLoading: rulesLoading, refetch: rRules } = useGetCommissionRulesQuery();
  const { data: commissions = [], isLoading: commLoading, refetch: rComm } = useGetCommissionsQuery();
  const [createRule] = useCreateCommissionRuleMutation();
  const [compute] = useComputeCommissionsMutation();
  const [pay] = usePayCommissionMutation();
  const { open: openPeek } = useDrawerPeek();

  const ruleColumns = useMemo<ColumnDef<Rule, any>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Name",
        cell: (c) => <span style={{ fontWeight: 500 }}>{c.getValue() as string}</span>,
      },
      { accessorKey: "percentage", header: "%", cell: (c) => `${c.getValue()}%` },
      { accessorKey: "min_amount", header: "Min", cell: (c) => `$${c.getValue()}` },
      {
        accessorKey: "max_amount",
        header: "Max",
        cell: (c) => {
          const v = c.getValue() as number | undefined;
          return v ? `$${v}` : "—";
        },
      },
      {
        accessorKey: "is_active",
        header: "Active",
        cell: (c) => (c.getValue() ? "Yes" : "No"),
      },
    ],
    [],
  );

  const commissionColumns = useMemo<ColumnDef<Commission, any>[]>(
    () => [
      {
        accessorKey: "user_id",
        header: "User",
        cell: (c) => <span style={{ fontSize: "0.75rem" }}>{(c.getValue() as string).slice(0, 8)}…</span>,
      },
      {
        accessorKey: "base_amount",
        header: "Base",
        cell: (c) => {
          const v = c.getValue() as number | undefined;
          return `$${v?.toLocaleString() ?? 0}`;
        },
      },
      {
        accessorKey: "commission",
        header: "Commission",
        cell: (c) => {
          const v = c.getValue() as number | undefined;
          return <span style={{ fontWeight: 600 }}>${v?.toLocaleString()}</span>;
        },
      },
      {
        accessorKey: "paid",
        header: "Paid",
        cell: (c) =>
          c.getValue() ? (
            <span className="badge badge-green">Paid</span>
          ) : (
            <span className="badge badge-yellow">Due</span>
          ),
      },
      {
        id: "actions",
        header: "Actions",
        enableSorting: false,
        cell: (c) => {
          const row = c.row.original;
          return !row.paid ? (
            <button
              className="btn btn-sm"
              onClick={async (e) => {
                e.stopPropagation();
                await pay(row.id);
                rComm();
              }}
            >
              Mark paid
            </button>
          ) : null;
        },
      },
    ],
    [pay, rComm],
  );

  return (
    <div>
      <PageHeader title="Commissions" subtitle="Rules and payouts for sales compensation." />
      <CommandBar
        items={[
          {
            key: "compute", label: "Compute for won opps",
            onClick: async () => {
              const r: any = await compute();
              await notifyUser({ title: "Commissions computed", description: `Computed ${r.data?.created || 0}` });
              rComm();
            },
          },
          {
            key: "rule", label: "New rule", variant: "primary",
            onClick: async () => {
              const v = await promptForValues({
                title: "New commission rule",
                submitLabel: "Create",
                fields: [
                  { name: "name", label: "Rule name", required: true },
                  { name: "percentage", label: "Percentage", kind: "number", required: true, step: 0.1, placeholder: "e.g. 10" },
                ],
              });
              if (!v) return;
              const percentage = parseFloat(v.percentage || "0");
              await createRule({ name: v.name, percentage, min_amount: 0 });
              rRules();
            },
          },
        ]}
      />
      <div style={{ marginBottom: "1rem" }}>
        <h3 style={{ marginBottom: "0.75rem" }}>Rules</h3>
        <DataTable
          columns={ruleColumns}
          data={rules as Rule[]}
          isLoading={rulesLoading}
          emptyTitle="No rules yet"
          emptyDescription="Add a commission rule to start computing payouts."
        />
      </div>
      <div>
        <h3 style={{ marginBottom: "0.5rem" }}>Payouts</h3>
        <DataTable
          columns={commissionColumns}
          data={commissions as Commission[]}
          isLoading={commLoading}
          emptyTitle="No commissions yet"
          emptyDescription="Compute commissions after closing won opportunities."
          onRowClick={(row) => openPeek("commission", row.id)}
        />
      </div>
    </div>
  );
}
