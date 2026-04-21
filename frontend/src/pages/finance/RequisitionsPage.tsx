import {
  useGetRequisitionsQuery, useCreateRequisitionMutation,
  useUpdateRequisitionStatusMutation, useConvertRequisitionMutation,
  useGetVendorsQuery,
} from "../../services/api";
import { useProjectContext } from "../../shell/useProjectContext";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";

const REQ_STATUSES = ["draft", "submitted", "approved", "rejected", "converted"];

export default function RequisitionsPage() {
  const projectId = useProjectContext();
  const { data: reqs = [], refetch } = useGetRequisitionsQuery();
  const { data: vendors = [] } = useGetVendorsQuery();
  const [createReq] = useCreateRequisitionMutation();
  const [updateStatus] = useUpdateRequisitionStatusMutation();
  const [convert] = useConvertRequisitionMutation();

  return (
    <div>
      <PageHeader title="Purchase requisitions" subtitle="Internal requests that convert to POs once approved." />
      <CommandBar
        items={[
          {
            key: "new", label: "New requisition", variant: "primary",
            onClick: async () => {
              const req_number = prompt("Requisition #:") || `REQ-${Date.now().toString().slice(-6)}`;
              const description = prompt("Item description:"); if (!description) return;
              const quantity = parseFloat(prompt("Quantity:") || "1");
              const unit_price = parseFloat(prompt("Unit price:") || "0");
              const justification = prompt("Justification:") || "";
              await createReq({
                project_id: projectId, req_number, justification,
                items: [{ description, quantity, unit_price }],
              });
              refetch();
            },
          },
        ]}
      />
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>Number</th><th>Status</th><th>Amount</th><th>Needed by</th><th>Actions</th></tr></thead>
          <tbody>
            {reqs.map((r: any) => (
              <tr key={r.id}>
                <td style={{ fontWeight: 500 }}>{r.req_number}</td>
                <td>
                  <select value={r.status} onChange={(e) => { updateStatus({ id: r.id, status: e.target.value }); refetch(); }} style={{ fontSize: "0.8rem", padding: "0.2rem" }}>
                    {REQ_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </td>
                <td style={{ fontWeight: 600 }}>${r.estimated_amount?.toLocaleString()}</td>
                <td>{r.needed_by || "-"}</td>
                <td>
                  {r.status === "approved" && !r.converted_po_id && vendors.length > 0 && (
                    <button className="btn btn-sm" onClick={async () => {
                      await convert({ id: r.id, body: { vendor_id: vendors[0].id } });
                      refetch();
                    }}>→ PO</button>
                  )}
                  {r.converted_po_id && <span className="badge badge-green">Converted</span>}
                </td>
              </tr>
            ))}
            {reqs.length === 0 && <tr><td colSpan={5} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No requisitions.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
