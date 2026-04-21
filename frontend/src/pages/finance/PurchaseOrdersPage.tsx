import { useGetPurchaseOrdersQuery, useCreatePurchaseOrderMutation, useGetVendorsQuery } from "../../services/api";
import { useProjectContext } from "../../shell/useProjectContext";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";

export default function PurchaseOrdersPage() {
  const projectId = useProjectContext();
  const { data: pos = [], refetch } = useGetPurchaseOrdersQuery(projectId);
  const { data: vendors = [] } = useGetVendorsQuery();
  const [createPO] = useCreatePurchaseOrderMutation();

  return (
    <div>
      <PageHeader title="Purchase orders" subtitle="Orders placed with vendors." />
      <CommandBar
        items={[
          {
            key: "new", label: "New PO", variant: "primary",
            disabled: vendors.length === 0,
            onClick: async () => {
              const po_number = prompt("PO number:") || `PO-${Date.now().toString().slice(-6)}`;
              const total_amount = parseFloat(prompt("Total amount:") || "0");
              const description = prompt("Description:") || "";
              await createPO({ po_number, total_amount, description, vendor_id: vendors[0].id, project_id: projectId });
              refetch();
            },
          },
        ]}
      />
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>PO number</th><th>Status</th><th>Amount</th><th>Description</th></tr></thead>
          <tbody>
            {pos.map((p: any) => (
              <tr key={p.id}>
                <td style={{ fontWeight: 500 }}>{p.po_number}</td>
                <td><span className="badge badge-blue">{p.status}</span></td>
                <td>${p.total_amount?.toLocaleString()}</td>
                <td>{p.description || "-"}</td>
              </tr>
            ))}
            {pos.length === 0 && <tr><td colSpan={4} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No purchase orders.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
