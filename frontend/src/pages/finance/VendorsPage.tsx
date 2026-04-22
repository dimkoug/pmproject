import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { useGetVendorsQuery, useCreateVendorMutation } from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";
import { downloadCsv } from "../../shell/csvExport";
import { promptForValues } from "../../shell/modalService";

type Vendor = {
  id: string;
  name: string;
  contact_person?: string;
  email?: string;
  phone?: string;
};

export default function VendorsPage() {
  const { data: vendors = [], isLoading, refetch } = useGetVendorsQuery();
  const [createVendor] = useCreateVendorMutation();
  const { open: openPeek } = useDrawerPeek();

  const columns = useMemo<ColumnDef<Vendor, any>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Name",
        cell: (c) => <span style={{ fontWeight: 500 }}>{c.getValue() as string}</span>,
      },
      { accessorKey: "contact_person", header: "Contact", cell: (c) => (c.getValue() as string) || "-" },
      { accessorKey: "email", header: "Email", cell: (c) => (c.getValue() as string) || "-" },
      { accessorKey: "phone", header: "Phone", cell: (c) => (c.getValue() as string) || "-" },
    ],
    [],
  );

  return (
    <div>
      <PageHeader title="Vendors" subtitle="Suppliers used in purchase orders and expenses." />
      <CommandBar
        items={[
          {
            key: "new", label: "New vendor", variant: "primary",
            onClick: async () => {
              const v = await promptForValues({
                title: "New vendor",
                submitLabel: "Create",
                fields: [
                  { name: "name", label: "Vendor name", required: true },
                ],
              });
              if (!v) return;
              await createVendor({ name: v.name });
              refetch();
            },
          },
          { key: "export", label: "Export CSV", onClick: () => downloadCsv("vendors") },
        ]}
      />
      <DataTable
        columns={columns}
        data={vendors as Vendor[]}
        isLoading={isLoading}
        emptyTitle="No vendors yet"
        emptyDescription="Add your first vendor to start creating purchase orders."
        onRowClick={(row) => openPeek("vendor", row.id)}
        stateStorageKey="finance-vendors"
      />
    </div>
  );
}
