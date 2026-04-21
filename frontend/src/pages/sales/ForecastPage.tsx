import { useGetForecastQuery } from "../../services/api";
import PageHeader from "../../shell/PageHeader";

export default function ForecastPage() {
  const { data: forecast } = useGetForecastQuery();
  if (!forecast) return <div>Loading…</div>;

  return (
    <div>
      <PageHeader title="Forecast" subtitle="Weighted pipeline by stage and expected close month." />
      <div className="stats-grid" style={{ marginBottom: "1rem" }}>
        <div className="stat-card">
          <div className="label">Weighted pipeline</div>
          <div className="value" style={{ color: "var(--success)" }}>${forecast.weighted_total?.toLocaleString()}</div>
        </div>
      </div>
      <div className="card">
        <h3 style={{ marginBottom: "0.75rem" }}>By stage</h3>
        <table>
          <thead><tr><th>Stage</th><th>Count</th><th>Amount</th><th>Weighted</th></tr></thead>
          <tbody>
            {forecast.by_stage?.map((s: any) => (
              <tr key={s.stage}>
                <td><span className="badge badge-blue">{s.stage.replace(/_/g, " ")}</span></td>
                <td>{s.count}</td>
                <td>${s.amount?.toLocaleString()}</td>
                <td style={{ fontWeight: 600 }}>${s.weighted?.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {forecast.by_month?.length > 0 && (
        <div className="card" style={{ marginTop: "1rem" }}>
          <h3 style={{ marginBottom: "0.75rem" }}>By expected close month</h3>
          <table>
            <thead><tr><th>Month</th><th>Count</th><th>Amount</th><th>Weighted</th></tr></thead>
            <tbody>
              {forecast.by_month.map((m: any) => (
                <tr key={m.month}>
                  <td>{m.month}</td>
                  <td>{m.count}</td>
                  <td>${m.amount?.toLocaleString()}</td>
                  <td style={{ fontWeight: 600 }}>${m.weighted?.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
