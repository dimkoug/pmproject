import { useGetCompaniesQuery, useCreateCompanyMutation } from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";

export default function CompaniesPage() {
  const { data: companies = [], refetch } = useGetCompaniesQuery();
  const [createCompany] = useCreateCompanyMutation();

  return (
    <div>
      <PageHeader title="Companies" subtitle="Customer and prospect organisations." />
      <CommandBar
        items={[
          {
            key: "new", label: "New company", variant: "primary",
            onClick: async () => {
              const name = prompt("Company name:"); if (!name) return;
              const industry = prompt("Industry (optional):") || undefined;
              await createCompany({ name, industry });
              refetch();
            },
          },
        ]}
      />
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>Name</th><th>Industry</th><th>Website</th><th>Revenue</th><th>Employees</th></tr></thead>
          <tbody>
            {companies.map((c: any) => (
              <tr key={c.id}>
                <td style={{ fontWeight: 500 }}>{c.name}</td>
                <td>{c.industry || "-"}</td>
                <td>{c.website || "-"}</td>
                <td>{c.annual_revenue ? `$${c.annual_revenue.toLocaleString()}` : "-"}</td>
                <td>{c.employee_count || "-"}</td>
              </tr>
            ))}
            {companies.length === 0 && <tr><td colSpan={5} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No companies yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
