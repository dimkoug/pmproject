import { useParams } from "react-router-dom";
import { useGetBurndownQuery } from "../services/api";
import BurndownChart from "../components/charts/BurndownChart";

export default function BurndownPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data, isLoading } = useGetBurndownQuery(projectId!);

  if (isLoading) return <p style={{ color: "var(--gray-400)", padding: "2rem 0" }}>Loading...</p>;

  const points = data?.points || [];
  const total = data?.total_points || 0;
  const done = data?.done_points || 0;

  return (
    <div>
      <div style={{ marginBottom: "1.5rem" }}>
        <h2 style={{ fontSize: "1.4rem", fontWeight: 700, letterSpacing: "-0.02em", marginBottom: "0.3rem" }}>Burndown Chart</h2>
        <p style={{ color: "var(--gray-400)", fontSize: "0.85rem" }}>Track progress over time for agile delivery</p>
      </div>

      <div className="stats-grid">
        <div className="stat-card"><div className="label">Total Points</div><div className="value">{total}</div></div>
        <div className="stat-card"><div className="label">Completed</div><div className="value">{done}</div></div>
        <div className="stat-card"><div className="label">Remaining</div><div className="value">{total - done}</div></div>
        <div className="stat-card"><div className="label">Burn Rate</div><div className="value">{total > 0 ? Math.round((done / total) * 100) : 0}%</div></div>
      </div>

      {points.length === 0 ? (
        <div className="empty-state"><p>Complete tasks with story points to see burndown data.</p></div>
      ) : (
        <div className="card">
          <h3 style={{ marginBottom: "1rem" }}>Burndown / Burnup</h3>
          <BurndownChart points={points} />
        </div>
      )}
    </div>
  );
}
