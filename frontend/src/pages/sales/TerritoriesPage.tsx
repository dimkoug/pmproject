import {
  useGetTerritoriesQuery, useCreateTerritoryMutation, useAutoAssignLeadsMutation,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";

export default function TerritoriesPage() {
  const { data: territories = [], refetch } = useGetTerritoriesQuery();
  const [createTerritory] = useCreateTerritoryMutation();
  const [autoAssign] = useAutoAssignLeadsMutation();

  return (
    <div>
      <PageHeader title="Territories" subtitle="Rule-based lead routing (industry, region, revenue)." />
      <CommandBar
        items={[
          {
            key: "auto", label: "Auto-assign leads",
            onClick: async () => {
              const r: any = await autoAssign();
              alert(`Assigned ${r.data?.assigned || 0} leads`);
            },
          },
          {
            key: "new", label: "New territory", variant: "primary",
            onClick: async () => {
              const name = prompt("Territory name:"); if (!name) return;
              const industry = prompt("Match industry (optional):") || undefined;
              const minRev = parseFloat(prompt("Min revenue (optional):") || "0");
              await createTerritory({ name, rule_industry: industry, rule_min_revenue: minRev || undefined });
              refetch();
            },
          },
        ]}
      />
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>Name</th><th>Region</th><th>Industry</th><th>Min revenue</th><th>Owner</th></tr></thead>
          <tbody>
            {territories.map((t: any) => (
              <tr key={t.id}>
                <td style={{ fontWeight: 500 }}>{t.name}</td>
                <td>{t.rule_region || "-"}</td>
                <td>{t.rule_industry || "-"}</td>
                <td>{t.rule_min_revenue ? `$${t.rule_min_revenue?.toLocaleString()}` : "-"}</td>
                <td style={{ fontSize: "0.75rem" }}>{t.owner_id ? `${t.owner_id.slice(0, 8)}…` : "-"}</td>
              </tr>
            ))}
            {territories.length === 0 && <tr><td colSpan={5} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No territories.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
