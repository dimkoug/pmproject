import { useGetVendorsQuery, useCreateVendorMutation } from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import { downloadCsv } from "../../shell/csvExport";

export default function VendorsPage() {
  const { data: vendors = [], refetch } = useGetVendorsQuery();
  const [createVendor] = useCreateVendorMutation();

  return (
    <div>
      <PageHeader title="Vendors" subtitle="Suppliers used in purchase orders and expenses." />
      <CommandBar
        items={[
          {
            key: "new", label: "New vendor", variant: "primary",
            onClick: async () => {
              const name = prompt("Vendor name:"); if (!name) return;
              await createVendor({ name });
              refetch();
            },
          },
          { key: "export", label: "Export CSV", onClick: () => downloadCsv("vendors") },
        ]}
      />
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>Name</th><th>Contact</th><th>Email</th><th>Phone</th></tr></thead>
          <tbody>
            {vendors.map((v: any) => (
              <tr key={v.id}>
                <td style={{ fontWeight: 500 }}>{v.name}</td>
                <td>{v.contact_person || "-"}</td>
                <td>{v.email || "-"}</td>
                <td>{v.phone || "-"}</td>
              </tr>
            ))}
            {vendors.length === 0 && <tr><td colSpan={4} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No vendors.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
