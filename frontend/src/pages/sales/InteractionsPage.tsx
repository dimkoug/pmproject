import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { useGetInteractionsQuery, useCreateInteractionMutation } from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";
import { promptForValues } from "../../shell/modalService";

const INTERACTION_TYPES = ["call", "email", "meeting", "note", "demo"];

type Interaction = {
  id: string;
  interaction_type: string;
  subject: string;
  interaction_date?: string;
  body?: string;
};

export default function InteractionsPage() {
  const { data: interactions = [], isLoading, refetch } = useGetInteractionsQuery({});
  const [createInteraction] = useCreateInteractionMutation();
  const { open: openPeek } = useDrawerPeek();

  const columns = useMemo<ColumnDef<Interaction, any>[]>(
    () => [
      {
        accessorKey: "interaction_type",
        header: "Type",
        cell: (c) => <span className="badge badge-blue">{c.getValue() as string}</span>,
      },
      {
        accessorKey: "subject",
        header: "Subject",
        cell: (c) => <span style={{ fontWeight: 500 }}>{c.getValue() as string}</span>,
      },
      {
        accessorKey: "interaction_date",
        header: "Date",
        cell: (c) => (c.getValue() as string) || "-",
      },
      {
        accessorKey: "body",
        header: "Notes",
        cell: (c) => {
          const v = c.getValue() as string | undefined;
          return <span style={{ fontSize: "0.82rem", color: "var(--gray-500)" }}>{v?.slice(0, 80) || "-"}</span>;
        },
      },
    ],
    [],
  );

  return (
    <div>
      <PageHeader title="Interactions" subtitle="Logged calls, emails, meetings, demos, and notes." />
      <CommandBar
        items={[
          {
            key: "new", label: "Log interaction", variant: "primary",
            onClick: async () => {
              const v = await promptForValues({
                title: "Log interaction",
                submitLabel: "Log",
                fields: [
                  { name: "subject", label: "Subject", required: true },
                  {
                    name: "interaction_type", label: "Type", kind: "select", defaultValue: "note",
                    options: INTERACTION_TYPES.map((t) => ({ value: t, label: t })),
                  },
                  { name: "body", label: "Notes", kind: "textarea", placeholder: "Optional" },
                ],
              });
              if (!v) return;
              await createInteraction({
                subject: v.subject,
                interaction_type: v.interaction_type || "note",
                body: v.body || "",
              });
              refetch();
            },
          },
        ]}
      />
      <DataTable
        columns={columns}
        data={interactions as Interaction[]}
        isLoading={isLoading}
        emptyTitle="No interactions logged"
        emptyDescription="Log your first call, email, or meeting to track engagement."
        onRowClick={(row) => openPeek("interaction", row.id)}
      />
    </div>
  );
}
