import {
  useGetLeadsQuery, useCreateLeadMutation, useUpdateLeadStatusMutation,
  useScoreAllLeadsMutation,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";

const LEAD_STATUSES = ["new", "contacted", "qualified", "unqualified", "converted"];
const LEAD_SOURCES = ["website", "referral", "cold_call", "advertising", "social_media", "event", "other"];

export default function LeadsPage() {
  const { data: leads = [], refetch } = useGetLeadsQuery();
  const [createLead] = useCreateLeadMutation();
  const [updateStatus] = useUpdateLeadStatusMutation();
  const [scoreAll] = useScoreAllLeadsMutation();

  return (
    <div>
      <PageHeader title="Leads" subtitle="Unqualified contacts entering the pipeline." />
      <CommandBar
        items={[
          {
            key: "score", label: "Re-score all",
            onClick: async () => { await scoreAll(); alert("Re-scored all leads"); refetch(); },
          },
          {
            key: "new", label: "New lead", variant: "primary",
            onClick: async () => {
              const contact_name = prompt("Contact name:"); if (!contact_name) return;
              const email = prompt("Email:") || "";
              const source = prompt(`Source (${LEAD_SOURCES.join("/")}):`, "other") || "other";
              await createLead({ contact_name, email, source });
              refetch();
            },
          },
        ]}
      />
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>Name</th><th>Company</th><th>Source</th><th>Status</th><th>Value</th></tr></thead>
          <tbody>
            {leads.map((l: any) => (
              <tr key={l.id}>
                <td style={{ fontWeight: 500 }}>{l.contact_name}</td>
                <td>{l.company_name || "-"}</td>
                <td><span className="badge badge-gray">{l.source}</span></td>
                <td>
                  <select value={l.status} onChange={(e) => { updateStatus({ id: l.id, status: e.target.value }); refetch(); }} style={{ fontSize: "0.8rem", padding: "0.2rem" }}>
                    {LEAD_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </td>
                <td>{l.estimated_value ? `$${l.estimated_value.toLocaleString()}` : "-"}</td>
              </tr>
            ))}
            {leads.length === 0 && <tr><td colSpan={5} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No leads yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
