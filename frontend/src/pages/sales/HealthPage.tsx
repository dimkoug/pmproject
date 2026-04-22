import { useGetHealthQuery, useComputeHealthMutation } from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import { notifyUser } from "../../shell/modalService";

export default function HealthPage() {
  const { data: health = [], refetch } = useGetHealthQuery();
  const [computeHealth] = useComputeHealthMutation();

  return (
    <div>
      <PageHeader title="Account health" subtitle="Per-company health scores computed from interactions, renewals, and activity." />
      <CommandBar
        items={[
          {
            key: "compute", label: "Compute snapshots", variant: "primary",
            onClick: async () => {
              const r: any = await computeHealth();
              await notifyUser({ title: "Snapshots computed", description: `Created ${r.data?.snapshots || 0} snapshots` });
              refetch();
            },
          },
        ]}
      />
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>Company</th><th>Score</th><th>Factors</th><th>Date</th></tr></thead>
          <tbody>
            {health.map((h: any) => (
              <tr key={h.company_id}>
                <td style={{ fontWeight: 500 }}>{h.name}</td>
                <td style={{ fontWeight: 700, color: h.score >= 70 ? "var(--success)" : h.score >= 40 ? "var(--warning)" : "var(--danger)" }}>{h.score}</td>
                <td style={{ fontSize: "0.82rem", color: "var(--gray-500)" }}>{h.factors || "-"}</td>
                <td>{h.date}</td>
              </tr>
            ))}
            {health.length === 0 && <tr><td colSpan={4} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No snapshots. Click "Compute snapshots" above.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
