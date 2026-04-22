import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { useGetSignaturesQuery, useCreateSignatureMutation } from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";
import { promptForValues } from "../../shell/modalService";

type Signature = {
  id: string;
  signer_email: string;
  document_id: string;
  status: string;
  signed_at?: string;
  token?: string;
};

export default function SignaturesPage() {
  const { data: sigs = [], isLoading, refetch } = useGetSignaturesQuery();
  const [createSig] = useCreateSignatureMutation();
  const { open: openPeek } = useDrawerPeek();

  const columns = useMemo<ColumnDef<Signature, any>[]>(
    () => [
      { accessorKey: "signer_email", header: "Signer" },
      {
        accessorKey: "document_id",
        header: "Document",
        cell: (c) => <span style={{ fontSize: "0.75rem" }}>{(c.getValue() as string).slice(0, 8)}…</span>,
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: (c) => {
          const v = c.getValue() as string;
          return (
            <span className={`badge ${v === "signed" ? "badge-green" : v === "declined" ? "badge-red" : "badge-yellow"}`}>
              {v}
            </span>
          );
        },
      },
      {
        accessorKey: "signed_at",
        header: "Signed",
        cell: (c) => {
          const v = c.getValue() as string | undefined;
          return v ? new Date(v).toLocaleDateString() : "-";
        },
      },
      {
        accessorKey: "token",
        header: "Link",
        cell: (c) => {
          const v = c.getValue() as string | undefined;
          return <span style={{ fontSize: "0.72rem", fontFamily: "monospace" }}>{v?.slice(0, 16)}…</span>;
        },
      },
    ],
    [],
  );

  return (
    <div>
      <PageHeader title="E-Signature requests" subtitle="Send documents for signature and track completion." />
      <CommandBar
        items={[
          {
            key: "request", label: "Request signature", variant: "primary",
            onClick: async () => {
              const v = await promptForValues({
                title: "Request signature",
                submitLabel: "Send",
                fields: [
                  { name: "docId", label: "Document ID", required: true },
                  { name: "email", label: "Signer email", kind: "email", required: true },
                ],
              });
              if (!v) return;
              await createSig({ document_id: v.docId, signer_email: v.email });
              refetch();
            },
          },
        ]}
      />
      <DataTable
        columns={columns}
        data={sigs as Signature[]}
        isLoading={isLoading}
        emptyTitle="No signature requests yet"
        emptyDescription="Send your first document for signature to get started."
        onRowClick={(row) => openPeek("signature", row.id)}
      />
    </div>
  );
}
