import { useParams } from "react-router-dom";
import { useGetEvmQuery } from "../services/api";
import EvmBarChart from "../components/charts/EvmBarChart";

const healthColor = (val: number, target: number = 1) => {
  if (val >= target * 0.95) return "var(--success)";
  if (val >= target * 0.8) return "var(--warning)";
  return "var(--danger)";
};

export default function EvmPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: evm, isLoading } = useGetEvmQuery(projectId!);

  if (isLoading) return <p style={{ color: "var(--gray-400)", padding: "2rem 0" }}>Loading...</p>;
  if (!evm || evm.bac === 0) return (
    <div>
      <h2 style={{ fontSize: "1.4rem", fontWeight: 700, marginBottom: "0.3rem" }}>Earned Value Management</h2>
      <div className="empty-state"><p>Set project budget and task planned/actual costs to see EVM analysis.</p></div>
    </div>
  );

  return (
    <div>
      <div style={{ marginBottom: "1.5rem" }}>
        <h2 style={{ fontSize: "1.4rem", fontWeight: 700, letterSpacing: "-0.02em", marginBottom: "0.3rem" }}>Earned Value Management</h2>
        <p style={{ color: "var(--gray-400)", fontSize: "0.85rem" }}>PMBOK cost and schedule performance analysis</p>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="label">BAC (Budget)</div>
          <div className="value">${evm.bac.toLocaleString()}</div>
        </div>
        <div className="stat-card">
          <div className="label">Earned Value (EV)</div>
          <div className="value">${evm.ev.toLocaleString()}</div>
          <div style={{ fontSize: "0.78rem", color: "var(--gray-500)" }}>{evm.percent_complete}% complete</div>
        </div>
        <div className="stat-card">
          <div className="label">Actual Cost (AC)</div>
          <div className="value">${evm.ac.toLocaleString()}</div>
          <div style={{ fontSize: "0.78rem", color: "var(--gray-500)" }}>{evm.percent_spent}% spent</div>
        </div>
        <div className="stat-card">
          <div className="label">Planned Value (PV)</div>
          <div className="value">${evm.pv.toLocaleString()}</div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <h3 style={{ marginBottom: "1rem" }}>Budget vs Earned vs Actual</h3>
        <EvmBarChart bac={evm.bac} pv={evm.pv} ev={evm.ev} ac={evm.ac} />
      </div>

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <h3 style={{ marginBottom: "1rem" }}>Performance Indices</h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "1rem" }}>
          <div style={{ padding: "1rem", border: "1px solid var(--gray-200)", borderRadius: "var(--radius-lg)" }}>
            <div style={{ fontSize: "0.78rem", color: "var(--gray-500)", marginBottom: "0.25rem" }}>CPI (Cost Performance)</div>
            <div style={{ fontSize: "2rem", fontWeight: 700, color: healthColor(evm.cpi) }}>{evm.cpi}</div>
            <div style={{ fontSize: "0.78rem", color: "var(--gray-500)" }}>{evm.cpi >= 1 ? "Under budget" : "Over budget"}</div>
          </div>
          <div style={{ padding: "1rem", border: "1px solid var(--gray-200)", borderRadius: "var(--radius-lg)" }}>
            <div style={{ fontSize: "0.78rem", color: "var(--gray-500)", marginBottom: "0.25rem" }}>SPI (Schedule Performance)</div>
            <div style={{ fontSize: "2rem", fontWeight: 700, color: healthColor(evm.spi) }}>{evm.spi}</div>
            <div style={{ fontSize: "0.78rem", color: "var(--gray-500)" }}>{evm.spi >= 1 ? "Ahead of schedule" : "Behind schedule"}</div>
          </div>
          <div style={{ padding: "1rem", border: "1px solid var(--gray-200)", borderRadius: "var(--radius-lg)" }}>
            <div style={{ fontSize: "0.78rem", color: "var(--gray-500)", marginBottom: "0.25rem" }}>TCPI (To Complete)</div>
            <div style={{ fontSize: "2rem", fontWeight: 700, color: healthColor(1, evm.tcpi) }}>{evm.tcpi}</div>
            <div style={{ fontSize: "0.78rem", color: "var(--gray-500)" }}>Performance needed to finish on budget</div>
          </div>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginBottom: "1rem" }}>Variances &amp; Forecasts</h3>
        <table>
          <thead><tr><th>Metric</th><th>Value</th><th>Interpretation</th></tr></thead>
          <tbody>
            <tr><td>Schedule Variance (SV)</td><td style={{ color: evm.sv >= 0 ? "var(--success)" : "var(--danger)", fontWeight: 600 }}>${evm.sv.toLocaleString()}</td><td>{evm.sv >= 0 ? "Ahead of schedule" : "Behind schedule"}</td></tr>
            <tr><td>Cost Variance (CV)</td><td style={{ color: evm.cv >= 0 ? "var(--success)" : "var(--danger)", fontWeight: 600 }}>${evm.cv.toLocaleString()}</td><td>{evm.cv >= 0 ? "Under budget" : "Over budget"}</td></tr>
            <tr><td>Estimate at Completion (EAC)</td><td style={{ fontWeight: 600 }}>${evm.eac.toLocaleString()}</td><td>{evm.eac <= evm.bac ? "Expected within budget" : `$${(evm.eac - evm.bac).toLocaleString()} over budget`}</td></tr>
            <tr><td>Estimate to Complete (ETC)</td><td style={{ fontWeight: 600 }}>${evm.etc.toLocaleString()}</td><td>Remaining cost to finish</td></tr>
            <tr><td>Variance at Completion (VAC)</td><td style={{ color: evm.vac >= 0 ? "var(--success)" : "var(--danger)", fontWeight: 600 }}>${evm.vac.toLocaleString()}</td><td>{evm.vac >= 0 ? "Expected savings" : "Expected overrun"}</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
