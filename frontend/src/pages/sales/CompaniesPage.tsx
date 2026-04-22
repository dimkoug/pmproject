import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { useGetCompaniesQuery, useCreateCompanyMutation } from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";
import { downloadCsv } from "../../shell/csvExport";
import { promptForValues } from "../../shell/modalService";

type Company = {
  id: string;
  name: string;
  industry?: string;
  website?: string;
  annual_revenue?: number;
  employee_count?: number;
};

export default function CompaniesPage() {
  const { data: companies = [], isLoading, refetch } = useGetCompaniesQuery();
  const [createCompany] = useCreateCompanyMutation();
  const { open: openPeek } = useDrawerPeek();

  const columns = useMemo<ColumnDef<Company, any>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Name",
        cell: (c) => <span style={{ fontWeight: 500 }}>{c.getValue() as string}</span>,
      },
      {
        accessorKey: "industry",
        header: "Industry",
        cell: (c) => (c.getValue() as string) || "-",
      },
      {
        accessorKey: "website",
        header: "Website",
        cell: (c) => (c.getValue() as string) || "-",
      },
      {
        accessorKey: "annual_revenue",
        header: "Revenue",
        cell: (c) => {
          const v = c.getValue() as number | undefined;
          return v ? `$${v.toLocaleString()}` : "-";
        },
      },
      {
        accessorKey: "employee_count",
        header: "Employees",
        cell: (c) => (c.getValue() as number | undefined) || "-",
      },
    ],
    [],
  );

  return (
    <div>
      <PageHeader title="Companies" subtitle="Customer and prospect organisations." />
      <CommandBar
        items={[
          {
            key: "new", label: "New company", variant: "primary",
            onClick: async () => {
              const v = await promptForValues({
                title: "New company",
                submitLabel: "Create",
                fields: [
                  { name: "name", label: "Company name", required: true },
                  { name: "industry", label: "Industry", placeholder: "Optional" },
                ],
              });
              if (!v) return;
              await createCompany({ name: v.name, industry: v.industry || undefined });
              refetch();
            },
          },
          { key: "export", label: "Export CSV", onClick: () => downloadCsv("companies") },
        ]}
      />
      <DataTable
        columns={columns}
        data={companies as Company[]}
        isLoading={isLoading}
        emptyTitle="No companies yet"
        emptyDescription="Create your first company to track customers and prospects."
        onRowClick={(row) => openPeek("company", row.id)}
      />
    </div>
  );
}
