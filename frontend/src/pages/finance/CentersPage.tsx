import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import {
  useGetCostCentersQuery,
  useCreateCostCenterMutation,
  useDeactivateCostCenterMutation,
  useGetProfitCentersQuery,
  useCreateProfitCenterMutation,
  useDeactivateProfitCenterMutation,
  useGetCenterPnlQuery,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { promptForValues, confirmAction } from "../../shell/modalService";
import { useFormat } from "../../i18n/format";

type Center = {
  id: string;
  code: string;
  name: string;
  description?: string | null;
  is_active: boolean;
};

export default function CentersPage() {
  const [tab, setTab] = useState<"cost" | "profit">("cost");
  const { data: costs = [], isLoading: lc } = useGetCostCentersQuery();
  const { data: profits = [], isLoading: lp } = useGetProfitCentersQuery();
  const [createCost] = useCreateCostCenterMutation();
  const [deactivateCost] = useDeactivateCostCenterMutation();
  const [createProfit] = useCreateProfitCenterMutation();
  const [deactivateProfit] = useDeactivateProfitCenterMutation();
  const { data: pnl = [] } = useGetCenterPnlQuery(tab);
  const { formatCurrency } = useFormat();

  const data = (tab === "cost" ? costs : profits) as Center[];
  const isLoading = tab === "cost" ? lc : lp;

  const create = tab === "cost" ? createCost : createProfit;
  const deactivate = tab === "cost" ? deactivateCost : deactivateProfit;

  const columns = useMemo<ColumnDef<Center, any>[]>(
    () => [
      {
        accessorKey: "code",
        header: "Code",
        cell: (c) => <code style={{ fontSize: "0.78rem" }}>{c.getValue() as string}</code>,
      },
      { accessorKey: "name", header: "Name", cell: (c) => <span style={{ fontWeight: 500 }}>{c.getValue() as string}</span> },
      { accessorKey: "description", header: "Description", cell: (c) => (c.getValue() as string) || "—" },
      {
        accessorKey: "is_active",
        header: "Status",
        cell: (c) =>
          c.getValue() ? (
            <span className="badge badge-green">active</span>
          ) : (
            <span className="badge badge-gray">inactive</span>
          ),
      },
      {
        id: "actions",
        header: "Actions",
        enableSorting: false,
        cell: (c) => {
          const row = c.row.original;
          if (!row.is_active) return null;
          return (
            <button
              className="btn btn-sm btn-danger"
              onClick={async (e) => {
                e.stopPropagation();
                const ok = await confirmAction({
                  title: `Deactivate ${row.code}?`,
                  description: "Existing journal lines stay attached. New lines won't be able to pick this center.",
                  submitLabel: "Deactivate",
                  dangerous: true,
                });
                if (!ok) return;
                await deactivate(row.id);
              }}
            >
              Deactivate
            </button>
          );
        },
      },
    ],
    [deactivate],
  );

  return (
    <div>
      <PageHeader
        title="Cost & profit centers"
        subtitle="Tag journal lines with a cost or profit center to slice your P&L by team / region / product line."
      />
      <div style={{ display: "inline-flex", gap: "0.25rem", marginBottom: "0.75rem" }}>
        <button
          className={`btn btn-sm ${tab === "cost" ? "btn-primary" : ""}`}
          onClick={() => setTab("cost")}
        >
          Cost centers
        </button>
        <button
          className={`btn btn-sm ${tab === "profit" ? "btn-primary" : ""}`}
          onClick={() => setTab("profit")}
        >
          Profit centers
        </button>
      </div>
      <CommandBar
        items={[
          {
            key: "new",
            label: tab === "cost" ? "New cost center" : "New profit center",
            variant: "primary",
            onClick: async () => {
              const v = await promptForValues({
                title: `New ${tab} center`,
                submitLabel: "Create",
                fields: [
                  { name: "code", label: "Code", required: true, placeholder: "e.g. ENG-NA" },
                  { name: "name", label: "Name", required: true },
                  { name: "description", label: "Description", kind: "textarea" },
                ],
              });
              if (!v) return;
              await create({ code: v.code, name: v.name, description: v.description || undefined });
            },
          },
        ]}
      />
      <DataTable
        columns={columns}
        data={data}
        isLoading={isLoading}
        emptyTitle={`No ${tab} centers yet`}
        emptyDescription="Create one and start attaching it to journal lines to enable per-center reporting."
      />

      <h2 style={{ fontSize: "1.1rem", fontWeight: 700, margin: "1.5rem 0 0.5rem" }}>
        P&L by {tab} center (posted journal lines)
      </h2>
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead>
            <tr>
              <th>Code</th>
              <th>Name</th>
              <th style={{ textAlign: "right" }}>Revenue</th>
              <th style={{ textAlign: "right" }}>Expense</th>
              <th style={{ textAlign: "right" }}>Net</th>
            </tr>
          </thead>
          <tbody>
            {(pnl as any[]).length === 0 ? (
              <tr><td colSpan={5} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>
                No posted entries with center tags yet.
              </td></tr>
            ) : (
              (pnl as any[]).map((row) => (
                <tr key={row.center_id || "_unassigned"}>
                  <td><code style={{ fontSize: "0.78rem" }}>{row.code}</code></td>
                  <td>{row.name}</td>
                  <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{formatCurrency(row.revenue)}</td>
                  <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{formatCurrency(row.expense)}</td>
                  <td style={{ textAlign: "right", fontWeight: 600, color: row.net >= 0 ? "var(--success)" : "var(--danger)", fontVariantNumeric: "tabular-nums" }}>
                    {formatCurrency(row.net)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
