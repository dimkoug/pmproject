import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { useGetFollowUpsDueQuery, useCompleteFollowUpMutation } from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import DataTable from "../../shell/DataTable";

type FollowUp = {
  id: string;
  subject: string;
  follow_up_date?: string;
  contact_id?: string;
};

export default function FollowUpsPage() {
  const { data: followUps = [], isLoading, refetch } = useGetFollowUpsDueQuery();
  const [completeFollowUp] = useCompleteFollowUpMutation();

  const columns = useMemo<ColumnDef<FollowUp, any>[]>(
    () => [
      { accessorKey: "subject", header: "Subject", cell: (c) => <span style={{ fontWeight: 500 }}>{c.getValue() as string}</span> },
      { accessorKey: "follow_up_date", header: "Due" },
      {
        accessorKey: "contact_id",
        header: "Contact",
        cell: (c) => {
          const v = c.getValue() as string | undefined;
          return <span style={{ fontSize: "0.75rem" }}>{v ? `${v.slice(0, 8)}…` : "-"}</span>;
        },
      },
      {
        id: "actions",
        header: "Actions",
        enableSorting: false,
        cell: (c) => (
          <button
            className="btn btn-sm"
            onClick={async (e) => {
              e.stopPropagation();
              await completeFollowUp(c.row.original.id);
              refetch();
            }}
          >
            Done
          </button>
        ),
      },
    ],
    [completeFollowUp, refetch],
  );

  return (
    <div>
      <PageHeader title="Follow-ups" subtitle="Due today and overdue interactions across all contacts." />
      <DataTable
        columns={columns}
        data={followUps as FollowUp[]}
        isLoading={isLoading}
        emptyTitle="Nothing due"
        emptyDescription="All follow-ups are cleared. Great work."
      />
    </div>
  );
}
