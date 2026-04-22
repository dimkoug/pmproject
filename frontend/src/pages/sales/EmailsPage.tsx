import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { useGetEmailsQuery, useIngestEmailMutation } from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";
import { promptForValues } from "../../shell/modalService";

type Email = {
  id: string;
  direction: string;
  subject?: string;
  from_email: string;
  to_email: string;
  sent_at?: string;
};

export default function EmailsPage() {
  const { data: emails = [], isLoading, refetch } = useGetEmailsQuery({});
  const [ingestEmail] = useIngestEmailMutation();
  const { open: openPeek } = useDrawerPeek();

  const columns = useMemo<ColumnDef<Email, any>[]>(
    () => [
      {
        accessorKey: "direction",
        header: "Direction",
        cell: (c) => {
          const v = c.getValue() as string;
          return <span className={`badge ${v === "inbound" ? "badge-blue" : "badge-green"}`}>{v}</span>;
        },
      },
      {
        accessorKey: "subject",
        header: "Subject",
        cell: (c) => <span style={{ fontWeight: 500 }}>{(c.getValue() as string) || "(no subject)"}</span>,
      },
      {
        accessorKey: "from_email",
        header: "From",
        cell: (c) => <span style={{ fontSize: "0.82rem" }}>{c.getValue() as string}</span>,
      },
      {
        accessorKey: "to_email",
        header: "To",
        cell: (c) => <span style={{ fontSize: "0.82rem" }}>{c.getValue() as string}</span>,
      },
      {
        accessorKey: "sent_at",
        header: "When",
        cell: (c) => {
          const v = c.getValue() as string | undefined;
          return <span style={{ fontSize: "0.75rem" }}>{v ? new Date(v).toLocaleDateString() : ""}</span>;
        },
      },
    ],
    [],
  );

  return (
    <div>
      <PageHeader title="Emails" subtitle="Contact-linked email log (inbound and outbound)." />
      <CommandBar
        items={[
          {
            key: "log", label: "Log email", variant: "primary",
            onClick: async () => {
              const v = await promptForValues({
                title: "Log email",
                submitLabel: "Log",
                fields: [
                  { name: "from", label: "From email", kind: "email", required: true },
                  { name: "to", label: "To email", kind: "email", required: true },
                  { name: "subject", label: "Subject" },
                  { name: "body", label: "Body", kind: "textarea", rows: 5 },
                ],
              });
              if (!v) return;
              await ingestEmail({
                direction: "inbound",
                from_email: v.from,
                to_email: v.to,
                subject: v.subject || "",
                body: v.body || "",
              });
              refetch();
            },
          },
        ]}
      />
      <DataTable
        columns={columns}
        data={emails as Email[]}
        isLoading={isLoading}
        emptyTitle="No emails logged"
        emptyDescription="Ingest an email to start building a timeline of outreach."
        onRowClick={(row) => openPeek("email", row.id)}
      />
    </div>
  );
}
