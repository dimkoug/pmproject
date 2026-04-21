import {
  useGetDepreciationQuery, useCreateDepreciationMutation, useRunDepreciationMutation,
  useGetAssetsQuery,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";

export default function DepreciationPage() {
  const { data: dep = [], refetch } = useGetDepreciationQuery();
  const { data: assets = [] } = useGetAssetsQuery();
  const [createDep] = useCreateDepreciationMutation();
  const [runDep] = useRunDepreciationMutation();

  return (
    <div>
      <PageHeader title="Depreciation schedules" subtitle="Asset depreciation runs posted to the journal." />
      <CommandBar
        items={[
          {
            key: "run", label: "Run now",
            onClick: async () => {
              const r: any = await runDep();
              alert(`Posted ${r.data?.schedules_posted || 0} / $${r.data?.total_depreciation || 0}`);
              refetch();
            },
          },
          {
            key: "new", label: "New schedule", variant: "primary",
            disabled: !assets.length,
            onClick: async () => {
              const asset_id = prompt("Asset ID:") || assets[0].id;
              const useful_life_months = parseInt(prompt("Useful life (months):") || "60");
              const salvage_value = parseFloat(prompt("Salvage value:") || "0");
              const start_date = prompt("Start date (YYYY-MM-DD):", new Date().toISOString().slice(0, 10)) || "";
              await createDep({ asset_id, useful_life_months, salvage_value, start_date });
              refetch();
            },
          },
        ]}
      />
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>Asset</th><th>Method</th><th>Life (mo)</th><th>Salvage</th><th>Accumulated</th><th>Last run</th></tr></thead>
          <tbody>
            {dep.map((d: any) => (
              <tr key={d.id}>
                <td style={{ fontSize: "0.75rem" }}>{d.asset_id.slice(0, 8)}…</td>
                <td><span className="badge badge-blue">{d.method}</span></td>
                <td>{d.useful_life_months}</td>
                <td>${d.salvage_value}</td>
                <td style={{ fontWeight: 600 }}>${d.accumulated?.toLocaleString()}</td>
                <td style={{ fontSize: "0.82rem" }}>{d.last_run || "—"}</td>
              </tr>
            ))}
            {dep.length === 0 && <tr><td colSpan={6} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No schedules.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
