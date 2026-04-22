import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import {
  useGetRfqsQuery,
  useCreateRfqMutation,
  useSendRfqMutation,
  useGetRfqQuery,
  useGetSupplierQuotesQuery,
  useSubmitSupplierQuoteMutation,
  useAwardRfqMutation,
  useGetVendorsQuery,
  useGetRequisitionsQuery,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { promptForValues, confirmAction, notifyUser } from "../../shell/modalService";
import { Icon } from "../../shell/icons";

type Rfq = {
  id: string;
  rfq_number: string;
  status: string;
  requisition_id?: string | null;
  issued_date?: string | null;
  response_due_date?: string | null;
  awarded_po_id?: string | null;
};

const STATUS_BADGE: Record<string, string> = {
  draft: "badge-gray",
  sent: "badge-blue",
  closed: "badge-yellow",
  awarded: "badge-green",
  cancelled: "badge-red",
};

export default function RfqsPage() {
  const { data: rfqs = [], isLoading, refetch } = useGetRfqsQuery();
  const { data: vendors = [] } = useGetVendorsQuery();
  const { data: requisitions = [] } = useGetRequisitionsQuery();
  const [createRfq] = useCreateRfqMutation();
  const [sendRfq] = useSendRfqMutation();
  const [submitQuote] = useSubmitSupplierQuoteMutation();
  const [awardRfq] = useAwardRfqMutation();
  const [expandedRfqId, setExpandedRfqId] = useState<string | null>(null);

  const vendorOptions = useMemo(
    () => (vendors as any[]).map((v) => ({ value: v.id, label: v.name })),
    [vendors],
  );
  const reqOptions = useMemo(
    () => (requisitions as any[]).map((r) => ({ value: r.id, label: `${r.req_number} · $${(r.estimated_amount || 0).toLocaleString()}` })),
    [requisitions],
  );

  const columns = useMemo<ColumnDef<Rfq, any>[]>(
    () => [
      {
        accessorKey: "rfq_number",
        header: "RFQ #",
        cell: (c) => <span style={{ fontWeight: 500 }}>{c.getValue() as string}</span>,
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: (c) => {
          const s = c.getValue() as string;
          return <span className={`badge ${STATUS_BADGE[s] || "badge-gray"}`}>{s}</span>;
        },
      },
      {
        accessorKey: "issued_date",
        header: "Issued",
        cell: (c) => (c.getValue() as string) || "-",
      },
      {
        accessorKey: "response_due_date",
        header: "Response due",
        cell: (c) => (c.getValue() as string) || "-",
      },
      {
        id: "actions",
        header: "Actions",
        enableSorting: false,
        cell: (c) => {
          const row = c.row.original;
          return (
            <div style={{ display: "inline-flex", gap: "0.25rem" }} onClick={(e) => e.stopPropagation()}>
              {row.status === "draft" && (
                <button
                  className="btn btn-sm"
                  onClick={async () => {
                    await sendRfq(row.id);
                    refetch();
                  }}
                >
                  Send
                </button>
              )}
              {["sent", "closed"].includes(row.status) && (
                <button
                  className="btn btn-sm"
                  onClick={() => setExpandedRfqId(expandedRfqId === row.id ? null : row.id)}
                >
                  {expandedRfqId === row.id ? "Hide" : "Compare"}
                </button>
              )}
              {row.awarded_po_id && (
                <span className="badge badge-green" style={{ display: "inline-flex", alignItems: "center", gap: "0.25rem" }}>
                  <Icon.Check size={12} /> PO created
                </span>
              )}
            </div>
          );
        },
      },
    ],
    [sendRfq, refetch, expandedRfqId],
  );

  return (
    <div>
      <PageHeader
        title="RFQs"
        subtitle="Request quotes from vendors, compare them side-by-side, award the winner, and auto-create the PO."
      />
      <CommandBar
        items={[
          {
            key: "new",
            label: "New RFQ",
            variant: "primary",
            onClick: async () => {
              const v = await promptForValues({
                title: "New RFQ",
                submitLabel: "Create draft",
                fields: [
                  { name: "rfq_number", label: "RFQ number", required: true },
                  { name: "requisition_id", label: "From requisition (optional)", kind: "select", options: reqOptions },
                  { name: "description", label: "Item description", required: true },
                  { name: "quantity", label: "Quantity", required: true, kind: "number", step: 1, defaultValue: "1" },
                  { name: "target_price", label: "Target unit price", kind: "number", step: 0.01 },
                  { name: "response_due_date", label: "Response due", kind: "date" },
                  { name: "vendor_ids", label: "Invite vendors (one per line, paste vendor ids)", kind: "textarea", helperText: "Leave blank to add vendors later." },
                ],
              });
              if (!v) return;
              const vendor_ids = (v.vendor_ids || "")
                .split(/[\n,]/)
                .map((s) => s.trim())
                .filter(Boolean);
              await createRfq({
                rfq_number: v.rfq_number,
                requisition_id: v.requisition_id || undefined,
                response_due_date: v.response_due_date || undefined,
                lines: [{
                  description: v.description,
                  quantity: parseFloat(v.quantity || "1"),
                  target_price: v.target_price ? parseFloat(v.target_price) : undefined,
                }],
                vendor_ids,
              });
              refetch();
            },
          },
        ]}
      />
      <DataTable
        columns={columns}
        data={rfqs as Rfq[]}
        isLoading={isLoading}
        emptyTitle="No RFQs yet"
        emptyDescription="Solicit vendor quotes to compare pricing and lead times before creating a purchase order."
      />
      {expandedRfqId && (
        <RfqCompareCard
          rfqId={expandedRfqId}
          onClose={() => setExpandedRfqId(null)}
          vendorOptions={vendorOptions}
          onSubmit={async (body) => {
            const r: any = await submitQuote({ rfqId: expandedRfqId, body });
            if (r.error) {
              await notifyUser({ title: "Failed to submit quote", description: (r.error as any)?.data?.detail });
            }
          }}
          onAward={async (supplierQuoteId) => {
            const ok = await confirmAction({
              title: "Award this quote?",
              description: "Awarding creates a PO for the winning supplier and closes the RFQ.",
              submitLabel: "Award",
            });
            if (!ok) return;
            const r: any = await awardRfq({ rfqId: expandedRfqId, body: { supplier_quote_id: supplierQuoteId } });
            if (r.error) {
              await notifyUser({ title: "Award failed", description: (r.error as any)?.data?.detail });
            } else {
              await notifyUser({ title: "PO created", description: r.data?.po_number });
              setExpandedRfqId(null);
              refetch();
            }
          }}
        />
      )}
    </div>
  );
}

function RfqCompareCard({
  rfqId,
  onClose,
  vendorOptions,
  onSubmit,
  onAward,
}: {
  rfqId: string;
  onClose: () => void;
  vendorOptions: { value: string; label: string }[];
  onSubmit: (body: any) => Promise<void>;
  onAward: (supplierQuoteId: string) => Promise<void>;
}) {
  const { data: rfq } = useGetRfqQuery(rfqId);
  const { data: quotes = [], refetch } = useGetSupplierQuotesQuery(rfqId);
  const lines = rfq?.lines || [];

  return (
    <div className="card" style={{ marginTop: "1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "0.75rem" }}>
        <div>
          <div style={{ fontSize: "0.95rem", fontWeight: 700 }}>Compare quotes — {rfq?.rfq_number}</div>
          <div style={{ fontSize: "0.78rem", color: "var(--gray-500)" }}>
            {lines.length} line{lines.length === 1 ? "" : "s"} · {quotes.length} supplier quote{quotes.length === 1 ? "" : "s"}
          </div>
        </div>
        <button className="btn btn-sm" onClick={onClose}>Close</button>
      </div>
      <div style={{ marginBottom: "1rem" }}>
        <button
          className="btn btn-sm"
          onClick={async () => {
            if (vendorOptions.length === 0) return;
            const fields: any[] = [
              { name: "vendor_id", label: "Vendor", required: true, kind: "select", options: vendorOptions },
              { name: "lead_time_days", label: "Lead time (days)", kind: "number", step: 1 },
              { name: "valid_until", label: "Valid until", kind: "date" },
              { name: "terms", label: "Terms", kind: "textarea" },
            ];
            for (const ln of lines) {
              fields.push({
                name: `price_${ln.id}`,
                label: `Unit price — ${ln.description} (qty ${ln.quantity})`,
                kind: "number",
                step: 0.01,
                required: true,
              });
            }
            const v = await promptForValues({
              title: "Submit supplier quote",
              submitLabel: "Submit",
              fields,
            });
            if (!v) return;
            const quoteLines = lines.map((ln: any) => ({
              rfq_line_id: ln.id,
              unit_price: parseFloat(v[`price_${ln.id}`] || "0"),
              lead_time_days: v.lead_time_days ? parseInt(v.lead_time_days, 10) : undefined,
            }));
            await onSubmit({
              vendor_id: v.vendor_id,
              lead_time_days: v.lead_time_days ? parseInt(v.lead_time_days, 10) : undefined,
              valid_until: v.valid_until || undefined,
              terms: v.terms || undefined,
              lines: quoteLines,
            });
            refetch();
          }}
        >
          + Add supplier quote
        </button>
      </div>
      {quotes.length === 0 ? (
        <div style={{ color: "var(--gray-500)", fontSize: "0.82rem" }}>No supplier quotes yet.</div>
      ) : (
        <table style={{ width: "100%" }}>
          <thead>
            <tr>
              <th>Vendor</th>
              <th>Lead time</th>
              <th>Total</th>
              <th>Status</th>
              <th style={{ textAlign: "right" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {quotes.map((q: any) => (
              <tr key={q.id}>
                <td style={{ fontWeight: 500 }}>
                  {vendorOptions.find((v) => v.value === q.vendor_id)?.label || q.vendor_id.slice(0, 8) + "…"}
                </td>
                <td>{q.lead_time_days ? `${q.lead_time_days} days` : "-"}</td>
                <td style={{ fontWeight: 600 }}>${(q.total || 0).toLocaleString()}</td>
                <td>
                  <span
                    className={`badge ${
                      q.status === "won" ? "badge-green" : q.status === "lost" ? "badge-gray" : "badge-blue"
                    }`}
                  >
                    {q.status}
                  </span>
                </td>
                <td style={{ textAlign: "right" }}>
                  {q.status === "submitted" && !rfq?.awarded_po_id && (
                    <button className="btn btn-sm btn-primary" onClick={() => onAward(q.id)}>
                      Award
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
