import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { useGetLocksQuery, useCheckinDocMutation } from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";

type Lock = {
  document_id: string;
  title?: string;
  user_id: string;
  locked_at?: string;
  note?: string;
};

export default function LocksPage() {
  const { data: locks = [], isLoading, refetch } = useGetLocksQuery();
  const [checkinDoc] = useCheckinDocMutation();
  const { open: openPeek } = useDrawerPeek();

  const columns = useMemo<ColumnDef<Lock, any>[]>(
    () => [
      {
        id: "document",
        header: "Document",
        accessorFn: (row) => row.title || row.document_id,
        cell: (c) => {
          const row = c.row.original;
          return (
            <span style={{ fontWeight: 500 }}>
              {row.title || row.document_id.slice(0, 8) + "…"}
            </span>
          );
        },
      },
      {
        accessorKey: "user_id",
        header: "User",
        cell: (c) => <span style={{ fontSize: "0.75rem" }}>{(c.getValue() as string).slice(0, 8)}…</span>,
      },
      {
        accessorKey: "locked_at",
        header: "Locked at",
        cell: (c) => {
          const v = c.getValue() as string | undefined;
          return <span style={{ fontSize: "0.82rem" }}>{v ? new Date(v).toLocaleString() : ""}</span>;
        },
      },
      {
        accessorKey: "note",
        header: "Note",
        cell: (c) => <span style={{ fontSize: "0.82rem" }}>{(c.getValue() as string) || "-"}</span>,
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
              await checkinDoc(c.row.original.document_id);
              refetch();
            }}
          >
            Force check-in
          </button>
        ),
      },
    ],
    [checkinDoc, refetch],
  );

  return (
    <div>
      <PageHeader title="Checked-out documents" subtitle="Documents currently locked by a user. Force check-in releases the lock." />
      <DataTable
        columns={columns}
        data={locks as Lock[]}
        isLoading={isLoading}
        emptyTitle="No active locks"
        emptyDescription="All documents are currently checked in."
        onRowClick={(row) => openPeek("lock", row.document_id)}
        rowKey={(row) => row.document_id}
      />
    </div>
  );
}
