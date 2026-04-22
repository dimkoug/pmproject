import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import {
  useGetContractsQuery, useCreateContractMutation, useGetContractMetricsQuery,
  useUpdateContractStatusMutation, useGetCompaniesQuery,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";
import { promptForValues, notifyUser } from "../../shell/modalService";

const CONTRACT_STATUSES = ["draft", "active", "renewing", "churned", "expired"];

type Contract = {
  id: string;
  contract_number: string;
  status: string;
  billing_cycle: string;
  amount?: number;
  mrr?: number;
  start_date?: string;
  end_date?: string;
};

export default function ContractsPage() {
  const { data: contracts = [], isLoading, refetch } = useGetContractsQuery();
  const { data: metrics } = useGetContractMetricsQuery();
  const { data: companies = [] } = useGetCompaniesQuery();
  const [createContract] = useCreateContractMutation();
  const [updateStatus] = useUpdateContractStatusMutation();
  const { open: openPeek } = useDrawerPeek();

  const columns = useMemo<ColumnDef<Contract, any>[]>(
    () => [
      {
        accessorKey: "contract_number",
        header: "Number",
        cell: (c) => <span style={{ fontWeight: 500 }}>{c.getValue() as string}</span>,
      },
      {
        accessorKey: "status",
        header: "Status",
        enableSorting: false,
        cell: (c) => {
          const row = c.row.original;
          return (
            <select
              value={row.status}
              onClick={(e) => e.stopPropagation()}
              onChange={(e) => { updateStatus({ id: row.id, status: e.target.value }); refetch(); }}
              style={{ fontSize: "0.8rem", padding: "0.2rem" }}
            >
              {CONTRACT_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          );
        },
      },
      {
        accessorKey: "billing_cycle",
        header: "Cycle",
        cell: (c) => <span className="badge badge-blue">{c.getValue() as string}</span>,
      },
      {
        accessorKey: "amount",
        header: "Amount",
        cell: (c) => {
          const v = c.getValue() as number | undefined;
          return <span style={{ fontWeight: 600 }}>${v?.toLocaleString()}</span>;
        },
      },
      {
        accessorKey: "mrr",
        header: "MRR",
        cell: (c) => {
          const v = c.getValue() as number | undefined;
          return `$${v?.toLocaleString() ?? 0}`;
        },
      },
      {
        id: "dates",
        header: "Dates",
        cell: (c) => {
          const r = c.row.original;
          return <span style={{ fontSize: "0.82rem" }}>{r.start_date} → {r.end_date || "—"}</span>;
        },
      },
    ],
    [updateStatus, refetch],
  );

  return (
    <div>
      <PageHeader title="Contracts" subtitle="Active customer agreements with MRR and ARR metrics." />
      <CommandBar
        items={[
          {
            key: "new", label: "New contract", variant: "primary",
            onClick: async () => {
              if (!companies.length) {
                await notifyUser({ title: "Missing data", description: "Add a company first" });
                return;
              }
              const v = await promptForValues({
                title: "New contract",
                submitLabel: "Create",
                fields: [
                  { name: "contract_number", label: "Contract #", placeholder: `C-${Date.now().toString().slice(-6)}` },
                  { name: "amount", label: "Amount", kind: "number", required: true, step: 0.01 },
                  {
                    name: "billing_cycle", label: "Billing", kind: "select", defaultValue: "monthly",
                    options: [
                      { value: "monthly", label: "Monthly" },
                      { value: "quarterly", label: "Quarterly" },
                      { value: "yearly", label: "Yearly" },
                      { value: "one_time", label: "One-time" },
                    ],
                  },
                  { name: "start_date", label: "Start date", kind: "date", defaultValue: new Date().toISOString().slice(0, 10) },
                ],
              });
              if (!v) return;
              const num = v.contract_number || `C-${Date.now().toString().slice(-6)}`;
              const amt = parseFloat(v.amount || "0");
              await createContract({
                company_id: companies[0].id,
                contract_number: num,
                amount: amt,
                billing_cycle: v.billing_cycle || "monthly",
                start_date: v.start_date || "",
                status: "active",
              });
              refetch();
            },
          },
        ]}
      />
      {metrics && (
        <div className="stats-grid" style={{ marginBottom: "1rem" }}>
          <div className="stat-card"><div className="label">Active</div><div className="value">{metrics.active_count}</div></div>
          <div className="stat-card"><div className="label">MRR</div><div className="value">${metrics.mrr?.toLocaleString()}</div></div>
          <div className="stat-card"><div className="label">ARR</div><div className="value" style={{ color: "var(--success)" }}>${metrics.arr?.toLocaleString()}</div></div>
          <div className="stat-card"><div className="label">Renewals ≤30d</div><div className="value" style={{ color: metrics.renewals_due_30d?.length ? "var(--warning)" : "inherit" }}>{metrics.renewals_due_30d?.length || 0}</div></div>
          <div className="stat-card"><div className="label">Churned</div><div className="value" style={{ color: "var(--danger)" }}>{metrics.churned_total}</div></div>
        </div>
      )}
      <DataTable
        columns={columns}
        data={contracts as Contract[]}
        isLoading={isLoading}
        emptyTitle="No contracts yet"
        emptyDescription="Create your first contract to start tracking MRR and ARR."
        onRowClick={(row) => openPeek("contract", row.id)}
      />
    </div>
  );
}
