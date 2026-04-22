import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { useGetScanResultsQuery, useScanVersionMutation } from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";
import { promptForValues, notifyUser } from "../../shell/modalService";

type Scan = {
  id: string;
  version_id: string;
  status: string;
  details?: string;
  scanned_at?: string;
};

export default function ScansPage() {
  const { data: scans = [], isLoading, refetch } = useGetScanResultsQuery();
  const [scanVersion] = useScanVersionMutation();
  const { open: openPeek } = useDrawerPeek();

  const columns = useMemo<ColumnDef<Scan, any>[]>(
    () => [
      {
        accessorKey: "version_id",
        header: "Version",
        cell: (c) => <span style={{ fontSize: "0.75rem" }}>{(c.getValue() as string).slice(0, 8)}…</span>,
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: (c) => {
          const v = c.getValue() as string;
          return (
            <span className={`badge ${v === "clean" ? "badge-green" : v === "infected" ? "badge-red" : "badge-gray"}`}>
              {v}
            </span>
          );
        },
      },
      {
        accessorKey: "details",
        header: "Details",
        cell: (c) => <span style={{ fontSize: "0.82rem" }}>{(c.getValue() as string) || "—"}</span>,
      },
      {
        accessorKey: "scanned_at",
        header: "Scanned at",
        cell: (c) => {
          const v = c.getValue() as string | undefined;
          return <span style={{ fontSize: "0.82rem" }}>{v ? new Date(v).toLocaleString() : ""}</span>;
        },
      },
    ],
    [],
  );

  return (
    <div>
      <PageHeader title="Virus scan results" subtitle="Per-version malware scan history." />
      <CommandBar
        items={[
          {
            key: "scan", label: "Scan version",
            onClick: async () => {
              const v = await promptForValues({
                title: "Scan version",
                submitLabel: "Scan",
                fields: [
                  { name: "vid", label: "Version ID", required: true },
                ],
              });
              if (!v) return;
              const r: any = await scanVersion(v.vid);
              await notifyUser({
                title: "Scan complete",
                description: `Status: ${r.data?.status}${r.data?.details ? " — " + r.data.details : ""}`,
              });
              refetch();
            },
          },
        ]}
      />
      <DataTable
        columns={columns}
        data={scans as Scan[]}
        isLoading={isLoading}
        emptyTitle="No scans yet"
        emptyDescription="Scan a document version to populate the history."
        onRowClick={(row) => openPeek("scan", row.id)}
      />
    </div>
  );
}
