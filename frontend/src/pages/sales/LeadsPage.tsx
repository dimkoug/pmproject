import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import {
  useGetLeadsQuery, useCreateLeadMutation, useUpdateLeadStatusMutation,
  useScoreAllLeadsMutation,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";
import { downloadCsv } from "../../shell/csvExport";
import { promptForValues, notifyUser } from "../../shell/modalService";

const LEAD_STATUSES = ["new", "contacted", "qualified", "unqualified", "converted"];
const LEAD_SOURCES = ["website", "referral", "cold_call", "advertising", "social_media", "event", "other"];

type Lead = {
  id: string;
  contact_name: string;
  company_name?: string;
  source: string;
  status: string;
  estimated_value?: number;
};

export default function LeadsPage() {
  const { data: leads = [], isLoading, refetch } = useGetLeadsQuery();
  const [createLead] = useCreateLeadMutation();
  const [updateStatus] = useUpdateLeadStatusMutation();
  const [scoreAll] = useScoreAllLeadsMutation();
  const { open: openPeek } = useDrawerPeek();

  const columns = useMemo<ColumnDef<Lead, any>[]>(
    () => [
      {
        accessorKey: "contact_name",
        header: "Name",
        cell: (c) => <span style={{ fontWeight: 500 }}>{c.getValue() as string}</span>,
      },
      {
        accessorKey: "company_name",
        header: "Company",
        cell: (c) => (c.getValue() as string) || "-",
      },
      {
        accessorKey: "source",
        header: "Source",
        cell: (c) => <span className="badge badge-gray">{c.getValue() as string}</span>,
      },
      {
        accessorKey: "status",
        header: "Status",
        enableSorting: false,
        cell: (c) => {
          const lead = c.row.original;
          return (
            <select
              value={lead.status}
              onClick={(e) => e.stopPropagation()}
              onChange={(e) => { updateStatus({ id: lead.id, status: e.target.value }); refetch(); }}
              style={{ fontSize: "0.8rem", padding: "0.2rem" }}
            >
              {LEAD_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          );
        },
      },
      {
        accessorKey: "estimated_value",
        header: "Value",
        cell: (c) => {
          const v = c.getValue() as number | undefined;
          return v ? `$${v.toLocaleString()}` : "-";
        },
      },
    ],
    [updateStatus, refetch],
  );

  return (
    <div>
      <PageHeader title="Leads" subtitle="Unqualified contacts entering the pipeline." />
      <CommandBar
        items={[
          {
            key: "score", label: "Re-score all",
            onClick: async () => {
              await scoreAll();
              await notifyUser({ title: "Re-scored all leads" });
              refetch();
            },
          },
          {
            key: "new", label: "New lead", variant: "primary",
            onClick: async () => {
              const v = await promptForValues({
                title: "New lead",
                submitLabel: "Create",
                fields: [
                  { name: "contact_name", label: "Contact name", required: true },
                  { name: "email", label: "Email", kind: "email" },
                  {
                    name: "source", label: "Source", kind: "select", defaultValue: "other",
                    options: LEAD_SOURCES.map((s) => ({ value: s, label: s })),
                  },
                ],
              });
              if (!v) return;
              await createLead({
                contact_name: v.contact_name,
                email: v.email || "",
                source: v.source || "other",
              });
              refetch();
            },
          },
          { key: "export", label: "Export CSV", onClick: () => downloadCsv("leads") },
        ]}
      />
      <DataTable
        columns={columns}
        data={leads as Lead[]}
        isLoading={isLoading}
        emptyTitle="No leads yet"
        emptyDescription="Capture your first lead to start qualifying prospects."
        onRowClick={(row) => openPeek("lead", row.id)}
        stateStorageKey="sales-leads"
      />
    </div>
  );
}
