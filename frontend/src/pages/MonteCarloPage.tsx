import { useState } from "react";
import { useParams } from "react-router-dom";
import { useGetMonteCarloQuery } from "../services/api";
import HistogramChart from "../components/charts/HistogramChart";

export default function MonteCarloPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [iterations, setIterations] = useState(1000);
  const { data: mc, isLoading } = useGetMonteCarloQuery({ projectId: projectId!, iterations });

  return (
    <div>
      <div style={{ marginBottom: "1.5rem" }}>
        <h2 style={{ fontSize: "1.4rem", fontWeight: 700, marginBottom: "0.3rem" }}>Monte Carlo Simulation</h2>
        <p style={{ color: "var(--gray-400)", fontSize: "0.85rem" }}>Probabilistic schedule and cost forecasting using triangular distributions</p>
      </div>

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <div style={{ display: "flex", gap: "0.75rem", alignItems: "flex-end" }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label>Iterations</label>
            <select value={iterations} onChange={(e) => setIterations(+e.target.value)} style={{ padding: "0.45rem 0.65rem", border: "1px solid var(--gray-300)", borderRadius: "var(--radius)", fontSize: "0.835rem", fontFamily: "var(--font-sans)" }}>
              <option value={500}>500</option>
              <option value={1000}>1,000</option>
              <option value={5000}>5,000</option>
              <option value={10000}>10,000</option>
            </select>
          </div>
        </div>
      </div>

      {isLoading ? <p style={{ color: "var(--gray-400)" }}>Running simulation...</p> : !mc ? null : (
        <>
          <div className="stats-grid">
            <div className="stat-card"><div className="label">Mean Duration</div><div className="value">{mc.duration.mean}d</div></div>
            <div className="stat-card"><div className="label">P50 (50% likely)</div><div className="value">{mc.duration.p50}d</div></div>
            <div className="stat-card"><div className="label">P90 (90% likely)</div><div className="value" style={{ color: "var(--warning)" }}>{mc.duration.p90}d</div></div>
            <div className="stat-card"><div className="label">P95 (95% likely)</div><div className="value" style={{ color: "var(--danger)" }}>{mc.duration.p95}d</div></div>
          </div>

          <div className="card" style={{ marginBottom: "1.25rem" }}>
            <h3 style={{ marginBottom: "1rem" }}>Duration Distribution ({mc.iterations} iterations)</h3>
            <HistogramChart buckets={mc.histogram} />
          </div>

          <div className="card" style={{ marginBottom: "1.25rem" }}>
            <h3 style={{ marginBottom: "0.75rem" }}>Percentile Table</h3>
            <table>
              <thead><tr><th>Percentile</th><th>Duration</th><th>Meaning</th></tr></thead>
              <tbody>
                <tr><td>P10</td><td>{mc.duration.p10}d</td><td>10% chance of finishing within this</td></tr>
                <tr><td>P50</td><td style={{ fontWeight: 600 }}>{mc.duration.p50}d</td><td>50% chance (median)</td></tr>
                <tr><td>P75</td><td>{mc.duration.p75}d</td><td>75% chance</td></tr>
                <tr><td>P90</td><td style={{ fontWeight: 600, color: "var(--warning)" }}>{mc.duration.p90}d</td><td>90% chance - typical commitment date</td></tr>
                <tr><td>P95</td><td style={{ color: "var(--danger)" }}>{mc.duration.p95}d</td><td>95% chance - conservative estimate</td></tr>
              </tbody>
            </table>
          </div>

          {mc.cost.mean > 0 && (
            <div className="card">
              <h3 style={{ marginBottom: "0.75rem" }}>Cost Forecast</h3>
              <div className="stats-grid">
                <div className="stat-card"><div className="label">Mean Cost</div><div className="value">${mc.cost.mean.toLocaleString()}</div></div>
                <div className="stat-card"><div className="label">P50 Cost</div><div className="value">${mc.cost.p50.toLocaleString()}</div></div>
                <div className="stat-card"><div className="label">P90 Cost</div><div className="value">${mc.cost.p90.toLocaleString()}</div></div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
