import { useGetCampaignsQuery, useCreateCampaignMutation } from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";

export default function CampaignsPage() {
  const { data: campaigns = [], refetch } = useGetCampaignsQuery();
  const [createCampaign] = useCreateCampaignMutation();

  return (
    <div>
      <PageHeader title="Campaigns" subtitle="Marketing programs with budget and spend tracking." />
      <CommandBar
        items={[
          {
            key: "new", label: "New campaign", variant: "primary",
            onClick: async () => {
              const name = prompt("Campaign name:"); if (!name) return;
              const budget = parseFloat(prompt("Budget:") || "0");
              await createCampaign({ name, budget, actual_cost: 0, status: "planned" });
              refetch();
            },
          },
        ]}
      />
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>Name</th><th>Status</th><th>Budget</th><th>Actual</th><th>Dates</th></tr></thead>
          <tbody>
            {campaigns.map((c: any) => (
              <tr key={c.id}>
                <td style={{ fontWeight: 500 }}>{c.name}</td>
                <td><span className="badge badge-blue">{c.status}</span></td>
                <td>${c.budget?.toLocaleString()}</td>
                <td>${c.actual_cost?.toLocaleString()}</td>
                <td style={{ fontSize: "0.82rem" }}>{c.start_date || "-"} → {c.end_date || "-"}</td>
              </tr>
            ))}
            {campaigns.length === 0 && <tr><td colSpan={5} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No campaigns.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
