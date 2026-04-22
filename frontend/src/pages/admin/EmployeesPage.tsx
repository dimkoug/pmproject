import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import {
  useGetEmployeesQuery,
  useCreateEmployeeMutation,
  useUpdateEmployeeMutation,
  useDeleteEmployeeMutation,
  useGetAdminUsersQuery,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";
import { promptForValues, confirmAction } from "../../shell/modalService";
import { useFormat } from "../../i18n/format";

type Employee = {
  id: string;
  user_id?: string | null;
  employee_number: string;
  first_name: string;
  last_name: string;
  full_name: string;
  email?: string | null;
  department?: string | null;
  job_title?: string | null;
  hire_date?: string | null;
  manager_id?: string | null;
  is_active: boolean;
};

export default function EmployeesPage() {
  const { data: employees = [], isLoading } = useGetEmployeesQuery();
  const { data: users = [] } = useGetAdminUsersQuery();
  const [createEmployee] = useCreateEmployeeMutation();
  const [updateEmployee] = useUpdateEmployeeMutation();
  const [deleteEmployee] = useDeleteEmployeeMutation();
  const { open: openPeek } = useDrawerPeek();
  const { formatDate } = useFormat();

  const userOpts = useMemo(
    () => (users as any[]).map((u) => ({ value: u.id, label: `${u.name || u.email}` })),
    [users],
  );
  const managerOpts = useMemo(
    () => (employees as Employee[]).map((e) => ({ value: e.id, label: `${e.full_name} (#${e.employee_number})` })),
    [employees],
  );

  const columns = useMemo<ColumnDef<Employee, any>[]>(
    () => [
      {
        accessorKey: "employee_number",
        header: "#",
        cell: (c) => <code style={{ fontSize: "0.78rem" }}>{c.getValue() as string}</code>,
      },
      {
        accessorKey: "full_name",
        header: "Name",
        cell: (c) => (
          <div>
            <div style={{ fontWeight: 500 }}>{c.row.original.full_name}</div>
            {c.row.original.email && <div style={{ fontSize: "0.72rem", color: "var(--gray-500)" }}>{c.row.original.email}</div>}
          </div>
        ),
      },
      { accessorKey: "department", header: "Department", cell: (c) => (c.getValue() as string) || "-" },
      { accessorKey: "job_title", header: "Job title", cell: (c) => (c.getValue() as string) || "-" },
      { accessorKey: "hire_date", header: "Hired", cell: (c) => formatDate(c.getValue() as string | undefined) },
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
          return (
            <div style={{ display: "inline-flex", gap: "0.25rem" }} onClick={(e) => e.stopPropagation()}>
              <button
                className="btn btn-sm"
                onClick={async () => {
                  const v = await promptForValues({
                    title: `Edit ${row.full_name}`,
                    submitLabel: "Save",
                    fields: [
                      { name: "first_name", label: "First name", required: true, defaultValue: row.first_name },
                      { name: "last_name", label: "Last name", required: true, defaultValue: row.last_name },
                      { name: "email", label: "Email", kind: "email", defaultValue: row.email || "" },
                      { name: "department", label: "Department", defaultValue: row.department || "" },
                      { name: "job_title", label: "Job title", defaultValue: row.job_title || "" },
                      {
                        name: "manager_id",
                        label: "Manager",
                        kind: "select",
                        options: managerOpts.filter((o) => o.value !== row.id),
                        defaultValue: row.manager_id || "",
                      },
                    ],
                  });
                  if (!v) return;
                  await updateEmployee({
                    id: row.id,
                    body: {
                      first_name: v.first_name,
                      last_name: v.last_name,
                      email: v.email || null,
                      department: v.department || null,
                      job_title: v.job_title || null,
                      manager_id: v.manager_id || null,
                    },
                  });
                }}
              >
                Edit
              </button>
              <button
                className="btn btn-sm"
                onClick={async () => {
                  await updateEmployee({
                    id: row.id,
                    body: {
                      is_active: !row.is_active,
                      ...(row.is_active ? { termination_date: new Date().toISOString().slice(0, 10) } : {}),
                    },
                  });
                }}
              >
                {row.is_active ? "Terminate" : "Reactivate"}
              </button>
              <button
                className="btn btn-sm btn-danger"
                onClick={async () => {
                  const ok = await confirmAction({
                    title: `Delete ${row.full_name}?`,
                    description: "This permanently removes the employee record. Use Terminate to deactivate without deleting.",
                    submitLabel: "Delete",
                    dangerous: true,
                  });
                  if (!ok) return;
                  await deleteEmployee(row.id);
                }}
              >
                Delete
              </button>
            </div>
          );
        },
      },
    ],
    [updateEmployee, deleteEmployee, managerOpts, formatDate],
  );

  return (
    <div>
      <PageHeader
        title="Employees"
        subtitle="Workforce directory. Optionally link to user accounts for self-service check-in and leave."
        breadcrumbs={[{ to: "/admin", label: "Admin" }, { to: "/admin/hr", label: "HR" }, { label: "Employees" }]}
      />
      <CommandBar
        items={[
          {
            key: "new",
            label: "New employee",
            variant: "primary",
            onClick: async () => {
              const v = await promptForValues({
                title: "New employee",
                submitLabel: "Create",
                fields: [
                  { name: "employee_number", label: "Employee #", required: true, placeholder: "e.g. E1042" },
                  { name: "first_name", label: "First name", required: true },
                  { name: "last_name", label: "Last name", required: true },
                  { name: "email", label: "Email", kind: "email" },
                  { name: "phone", label: "Phone" },
                  { name: "department", label: "Department" },
                  { name: "job_title", label: "Job title" },
                  { name: "hire_date", label: "Hire date", kind: "date" },
                  { name: "user_id", label: "Linked user (optional)", kind: "select", options: userOpts },
                ],
              });
              if (!v) return;
              await createEmployee({
                employee_number: v.employee_number,
                first_name: v.first_name,
                last_name: v.last_name,
                email: v.email || undefined,
                phone: v.phone || undefined,
                department: v.department || undefined,
                job_title: v.job_title || undefined,
                hire_date: v.hire_date || undefined,
                user_id: v.user_id || undefined,
              });
            },
          },
        ]}
      />
      <DataTable
        columns={columns}
        data={employees as Employee[]}
        isLoading={isLoading}
        emptyTitle="No employees yet"
        emptyDescription="Add your first employee to start tracking leave and attendance."
        onRowClick={(row) => openPeek("employee", row.id)}
      />
    </div>
  );
}
