import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import {
  useGetDripsQuery, useCreateDripMutation, useEnrollDripMutation, useDripTickMutation,
  useGetCrmContactsQuery,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";
import { promptForValues, notifyUser } from "../../shell/modalService";

type Drip = {
  id: string;
  name: string;
  step_count: number;
  is_active: boolean;
};

export default function DripsPage() {
  const { data: drips = [], isLoading, refetch } = useGetDripsQuery();
  const { data: contacts = [] } = useGetCrmContactsQuery(undefined);
  const [createDrip] = useCreateDripMutation();
  const [enrollDrip] = useEnrollDripMutation();
  const [dripTick] = useDripTickMutation();
  const { open: openPeek } = useDrawerPeek();

  const columns = useMemo<ColumnDef<Drip, any>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Name",
        cell: (c) => <span style={{ fontWeight: 500 }}>{c.getValue() as string}</span>,
      },
      { accessorKey: "step_count", header: "Steps" },
      {
        accessorKey: "is_active",
        header: "Active",
        cell: (c) => (c.getValue() ? "Yes" : "No"),
      },
      {
        id: "actions",
        header: "Actions",
        enableSorting: false,
        cell: (c) => {
          const d = c.row.original;
          return (
            <button
              className="btn btn-sm"
              onClick={async (e) => {
                e.stopPropagation();
                if (!contacts.length) {
                  await notifyUser({ title: "No contacts", description: "Add a contact first." });
                  return;
                }
                const v = await promptForValues({
                  title: "Enroll contact",
                  submitLabel: "Enroll",
                  fields: [
                    { name: "cid", label: "Contact ID", required: true, defaultValue: contacts[0].id },
                  ],
                });
                if (!v) return;
                const cid = v.cid || contacts[0].id;
                await enrollDrip({ sequence_id: d.id, contact_id: cid });
                await notifyUser({ title: "Enrolled" });
              }}
            >
              Enroll contact
            </button>
          );
        },
      },
    ],
    [contacts, enrollDrip],
  );

  return (
    <div>
      <PageHeader title="Drip sequences" subtitle="Automated scheduled email sequences enrolling contacts over time." />
      <CommandBar
        items={[
          {
            key: "tick", label: "Run tick",
            onClick: async () => {
              const r: any = await dripTick();
              await notifyUser({
                title: "Tick complete",
                description: `Advanced ${r.data?.advanced || 0}, sent ${r.data?.emails_sent || 0}`,
              });
            },
          },
          {
            key: "new", label: "New sequence", variant: "primary",
            onClick: async () => {
              const v = await promptForValues({
                title: "New drip sequence",
                submitLabel: "Create",
                fields: [
                  { name: "name", label: "Sequence name", required: true },
                  { name: "subject", label: "Step 1 subject", required: true },
                  { name: "body", label: "Step 1 body", kind: "textarea", rows: 5 },
                ],
              });
              if (!v) return;
              await createDrip({
                name: v.name,
                steps: [{ step_order: 0, delay_days: 0, subject: v.subject, body: v.body || "" }],
              });
              refetch();
            },
          },
        ]}
      />
      <DataTable
        columns={columns}
        data={drips as Drip[]}
        isLoading={isLoading}
        emptyTitle="No sequences yet"
        emptyDescription="Build your first drip to start nurturing contacts automatically."
        onRowClick={(row) => openPeek("drip", row.id)}
      />
    </div>
  );
}
