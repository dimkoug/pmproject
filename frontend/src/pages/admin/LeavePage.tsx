import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import {
  useGetLeaveRequestsQuery,
  useCreateLeaveRequestMutation,
  useDecideLeaveRequestMutation,
  useGetEmployeesQuery,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { promptForValues, confirmAction, notifyUser } from "../../shell/modalService";
import { useFormat } from "../../i18n/format";

type Leave = {
  id: string;
  employee_id: string;
  employee_name?: string | null;
  leave_type: string;
  start_date?: string | null;
  end_date?: string | null;
  days: number;
  reason?: string | null;
  status: string;
  approver_id?: string | null;
  decided_at?: string | null;
  decision_note?: string | null;
};

const STATUS_BADGE: Record<string, string> = {
  pending: "badge-yellow",
  approved: "badge-green",
  rejected: "badge-red",
  cancelled: "badge-gray",
};

const TYPE_OPTS = [
  { value: "vacation", label: "Vacation" },
  { value: "sick", label: "Sick" },
  { value: "personal", label: "Personal" },
  { value: "bereavement", label: "Bereavement" },
  { value: "maternity", label: "Maternity" },
  { value: "paternity", label: "Paternity" },
  { value: "unpaid", label: "Unpaid" },
  { value: "other", label: "Other" },
];

export default function LeavePage() {
  const { data: leaves = [], isLoading } = useGetLeaveRequestsQuery();
  const { data: employees = [] } = useGetEmployeesQuery();
  const [createLeave] = useCreateLeaveRequestMutation();
  const [decideLeave] = useDecideLeaveRequestMutation();
  const { formatDate } = useFormat();

  const employeeOpts = useMemo(
    () => (employees as any[]).map((e) => ({ value: e.id, label: `${e.full_name} (#${e.employee_number})` })),
    [employees],
  );

  const columns = useMemo<ColumnDef<Leave, any>[]>(
    () => [
      {
        accessorKey: "employee_name",
        header: "Employee",
        cell: (c) => <span style={{ fontWeight: 500 }}>{(c.getValue() as string) || "—"}</span>,
      },
      {
        accessorKey: "leave_type",
        header: "Type",
        cell: (c) => <span className="badge badge-gray">{c.getValue() as string}</span>,
      },
      {
        id: "dates",
        header: "Dates",
        cell: (c) => {
          const r = c.row.original;
          return `${formatDate(r.start_date)} → ${formatDate(r.end_date)}`;
        },
      },
      {
        accessorKey: "days",
        header: "Days",
        cell: (c) => <span style={{ fontWeight: 600 }}>{c.getValue() as number}</span>,
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: (c) => {
          const s = c.getValue() as string;
          return <span className={`badge ${STATUS_BADGE[s] || "badge-gray"}`}>{s}</span>;
        },
      },
      {
        accessorKey: "reason",
        header: "Reason",
        cell: (c) => {
          const v = (c.getValue() as string) || "";
          return v.length > 60 ? v.slice(0, 60) + "…" : v || "—";
        },
      },
      {
        id: "actions",
        header: "Actions",
        enableSorting: false,
        cell: (c) => {
          const row = c.row.original;
          if (row.status !== "pending") return null;
          return (
            <div style={{ display: "inline-flex", gap: "0.25rem" }} onClick={(e) => e.stopPropagation()}>
              <button
                className="btn btn-sm"
                onClick={async () => {
                  const v = await promptForValues({
                    title: `Approve ${row.employee_name}'s leave`,
                    description: `${row.days} day(s) ${formatDate(row.start_date)} → ${formatDate(row.end_date)}`,
                    submitLabel: "Approve",
                    fields: [{ name: "note", label: "Note (optional)", kind: "textarea" }],
                  });
                  if (!v) return;
                  await decideLeave({ id: row.id, body: { decision: "approved", note: v.note || null } });
                }}
              >
                Approve
              </button>
              <button
                className="btn btn-sm btn-danger"
                onClick={async () => {
                  const v = await promptForValues({
                    title: `Reject ${row.employee_name}'s leave`,
                    submitLabel: "Reject",
                    fields: [{ name: "note", label: "Reason (recommended)", kind: "textarea" }],
                  });
                  if (!v) return;
                  await decideLeave({ id: row.id, body: { decision: "rejected", note: v.note || null } });
                }}
              >
                Reject
              </button>
            </div>
          );
        },
      },
    ],
    [decideLeave, formatDate],
  );

  return (
    <div>
      <PageHeader
        title="Leave requests"
        subtitle="Pending requests need a decision; approved leaves count toward the on-leave-today widget."
        breadcrumbs={[{ to: "/admin", label: "Admin" }, { to: "/admin/hr", label: "HR" }, { label: "Leave" }]}
      />
      <CommandBar
        items={[
          {
            key: "new",
            label: "New leave request",
            variant: "primary",
            onClick: async () => {
              if (employeeOpts.length === 0) {
                await notifyUser({ title: "No employees", description: "Create an employee first." });
                return;
              }
              const v = await promptForValues({
                title: "New leave request",
                submitLabel: "Submit",
                fields: [
                  { name: "employee_id", label: "Employee", required: true, kind: "select", options: employeeOpts },
                  { name: "leave_type", label: "Type", required: true, kind: "select", options: TYPE_OPTS, defaultValue: "vacation" },
                  { name: "start_date", label: "Start", required: true, kind: "date" },
                  { name: "end_date", label: "End", required: true, kind: "date" },
                  { name: "reason", label: "Reason", kind: "textarea" },
                ],
              });
              if (!v) return;
              const r: any = await createLeave({
                employee_id: v.employee_id,
                leave_type: v.leave_type,
                start_date: v.start_date,
                end_date: v.end_date,
                reason: v.reason || undefined,
              });
              if (r.error) {
                await notifyUser({ title: "Failed", description: (r.error as any)?.data?.detail });
              }
            },
          },
        ]}
      />
      <DataTable
        columns={columns}
        data={leaves as Leave[]}
        isLoading={isLoading}
        emptyTitle="No leave requests"
        emptyDescription="Submit a leave request to test the approval workflow."
      />
    </div>
  );
}
