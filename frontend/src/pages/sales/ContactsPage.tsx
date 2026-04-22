import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { useGetCrmContactsQuery, useCreateCrmContactMutation } from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";
import { promptForValues } from "../../shell/modalService";

type Contact = {
  id: string;
  first_name: string;
  last_name?: string;
  email?: string;
  phone?: string;
  job_title?: string;
};

export default function ContactsPage() {
  const { data: contacts = [], isLoading, refetch } = useGetCrmContactsQuery(undefined);
  const [createContact] = useCreateCrmContactMutation();
  const { open: openPeek } = useDrawerPeek();

  const columns = useMemo<ColumnDef<Contact, any>[]>(
    () => [
      {
        id: "name",
        header: "Name",
        accessorFn: (row) => `${row.first_name} ${row.last_name || ""}`.trim(),
        cell: (c) => <span style={{ fontWeight: 500 }}>{c.getValue() as string}</span>,
      },
      {
        accessorKey: "email",
        header: "Email",
        cell: (c) => (c.getValue() as string) || "-",
      },
      {
        accessorKey: "phone",
        header: "Phone",
        cell: (c) => (c.getValue() as string) || "-",
      },
      {
        accessorKey: "job_title",
        header: "Title",
        cell: (c) => (c.getValue() as string) || "-",
      },
    ],
    [],
  );

  return (
    <div>
      <PageHeader title="Contacts" subtitle="People at customer and prospect companies." />
      <CommandBar
        items={[
          {
            key: "new", label: "New contact", variant: "primary",
            onClick: async () => {
              const v = await promptForValues({
                title: "New contact",
                submitLabel: "Create",
                fields: [
                  { name: "first_name", label: "First name", required: true },
                  { name: "last_name", label: "Last name" },
                  { name: "email", label: "Email", kind: "email" },
                ],
              });
              if (!v) return;
              await createContact({
                first_name: v.first_name,
                last_name: v.last_name || "",
                email: v.email || "",
              });
              refetch();
            },
          },
        ]}
      />
      <DataTable
        columns={columns}
        data={contacts as Contact[]}
        isLoading={isLoading}
        emptyTitle="No contacts yet"
        emptyDescription="Add your first contact to start tracking relationships."
        onRowClick={(row) => openPeek("contact", row.id)}
      />
    </div>
  );
}
