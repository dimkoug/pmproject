import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import {
  useGetAttendanceQuery,
  useCreateAttendanceMutation,
  useGetEmployeesQuery,
  useCheckInMutation,
  useCheckOutMutation,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { promptForValues, notifyUser } from "../../shell/modalService";
import { useFormat } from "../../i18n/format";
import { Icon } from "../../shell/icons";

type Att = {
  id: string;
  employee_id: string;
  employee_name?: string | null;
  work_date?: string | null;
  check_in?: string | null;
  check_out?: string | null;
  hours_worked?: number | null;
  source?: string | null;
};

const SOURCE_OPTS = [
  { value: "web", label: "Web" },
  { value: "mobile", label: "Mobile" },
  { value: "kiosk", label: "Kiosk" },
  { value: "import", label: "Import" },
  { value: "manual", label: "Manual" },
];

export default function AttendancePage() {
  const { data: rows = [], isLoading } = useGetAttendanceQuery();
  const { data: employees = [] } = useGetEmployeesQuery();
  const [createAttendance] = useCreateAttendanceMutation();
  const [checkIn] = useCheckInMutation();
  const [checkOut] = useCheckOutMutation();
  const { formatDate, formatTime } = useFormat();

  const employeeOpts = useMemo(
    () => (employees as any[]).map((e) => ({ value: e.id, label: `${e.full_name} (#${e.employee_number})` })),
    [employees],
  );

  const columns = useMemo<ColumnDef<Att, any>[]>(
    () => [
      {
        accessorKey: "employee_name",
        header: "Employee",
        cell: (c) => <span style={{ fontWeight: 500 }}>{(c.getValue() as string) || "—"}</span>,
      },
      {
        accessorKey: "work_date",
        header: "Date",
        cell: (c) => formatDate(c.getValue() as string | undefined),
      },
      {
        accessorKey: "check_in",
        header: "In",
        cell: (c) => formatTime(c.getValue() as string | undefined),
      },
      {
        accessorKey: "check_out",
        header: "Out",
        cell: (c) => formatTime(c.getValue() as string | undefined),
      },
      {
        accessorKey: "hours_worked",
        header: "Hours",
        cell: (c) => {
          const v = c.getValue() as number | null | undefined;
          return v != null ? <span style={{ fontWeight: 600 }}>{v.toFixed(2)}</span> : "—";
        },
      },
      {
        accessorKey: "source",
        header: "Source",
        cell: (c) => <span className="badge badge-gray">{c.getValue() as string}</span>,
      },
    ],
    [formatDate, formatTime],
  );

  return (
    <div>
      <PageHeader
        title="Attendance"
        subtitle="Daily check-in / check-out records. Self-service from the HR overview, or recorded manually here."
        breadcrumbs={[{ to: "/admin", label: "Admin" }, { to: "/admin/hr", label: "HR" }, { label: "Attendance" }]}
      />
      <CommandBar
        items={[
          {
            key: "self-checkin",
            label: "Check in",
            onClick: async () => {
              const r: any = await checkIn();
              if (r.error) {
                await notifyUser({ title: "Check-in failed", description: (r.error as any)?.data?.detail });
              } else {
                await notifyUser({ title: "Checked in" });
              }
            },
          },
          {
            key: "self-checkout",
            label: "Check out",
            onClick: async () => {
              const r: any = await checkOut();
              if (r.error) {
                await notifyUser({ title: "Check-out failed", description: (r.error as any)?.data?.detail });
              } else {
                await notifyUser({ title: "Checked out", description: r.data?.hours_worked ? `${r.data.hours_worked.toFixed(2)} hours` : "" });
              }
            },
          },
          {
            key: "new",
            label: "Record entry",
            variant: "primary",
            onClick: async () => {
              if (employeeOpts.length === 0) {
                await notifyUser({ title: "No employees", description: "Create an employee first." });
                return;
              }
              const v = await promptForValues({
                title: "Record attendance",
                submitLabel: "Save",
                fields: [
                  { name: "employee_id", label: "Employee", required: true, kind: "select", options: employeeOpts },
                  { name: "work_date", label: "Work date", required: true, kind: "date", defaultValue: new Date().toISOString().slice(0, 10) },
                  { name: "check_in", label: "Check-in (ISO datetime)", placeholder: "2026-04-22T09:00:00" },
                  { name: "check_out", label: "Check-out (ISO datetime)", placeholder: "2026-04-22T17:00:00" },
                  { name: "source", label: "Source", kind: "select", options: SOURCE_OPTS, defaultValue: "manual" },
                  { name: "notes", label: "Notes", kind: "textarea" },
                ],
              });
              if (!v) return;
              await createAttendance({
                employee_id: v.employee_id,
                work_date: v.work_date,
                check_in: v.check_in || undefined,
                check_out: v.check_out || undefined,
                source: v.source || "manual",
                notes: v.notes || undefined,
              });
            },
          },
        ]}
        right={
          <span style={{ fontSize: "0.78rem", color: "var(--gray-500)", display: "inline-flex", alignItems: "center", gap: "0.3rem" }}>
            <Icon.Info size={14} /> Check-in works only for users linked to an employee record.
          </span>
        }
      />
      <DataTable
        columns={columns}
        data={rows as Att[]}
        isLoading={isLoading}
        emptyTitle="No attendance records"
        emptyDescription="Click Check in to log your first entry, or record one manually."
      />
    </div>
  );
}
