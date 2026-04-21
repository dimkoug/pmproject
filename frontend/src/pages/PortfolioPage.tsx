import { useNavigate } from "react-router-dom";
import { useGetPortfolioQuery } from "../services/api";
import { useAppSelector, useAppDispatch } from "../app/hooks";
import { logout } from "../services/authSlice";

export default function PortfolioPage() {
  const { data: projects = [], isLoading } = useGetPortfolioQuery();
  const user = useAppSelector((s) => s.auth.user);
  const dispatch = useAppDispatch();
  const navigate = useNavigate();

  const handleLogout = () => { dispatch(logout()); navigate("/login"); };

  if (isLoading) return <p style={{ padding: "2rem", color: "var(--gray-400)" }}>Loading portfolio...</p>;

  const totalBudget = projects.reduce((s: number, p: any) => s + (p.budget || 0), 0);
  const totalTasks = projects.reduce((s: number, p: any) => s + p.total_tasks, 0);
  const totalDone = projects.reduce((s: number, p: any) => s + p.done_tasks, 0);
  const totalRisks = projects.reduce((s: number, p: any) => s + p.open_risks, 0);

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: "2.5rem 2rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.35rem" }}>
        <h1 style={{ fontSize: "1.6rem", fontWeight: 700, letterSpacing: "-0.03em" }}>Portfolio Dashboard</h1>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          {user && <span style={{ fontSize: "0.82rem", color: "var(--gray-500)", fontWeight: 500 }}>{user.name}</span>}
          <button className="btn" onClick={() => navigate("/")}>Projects</button>
          <button className="btn" onClick={handleLogout} style={{ color: "var(--gray-500)" }}>Sign out</button>
        </div>
      </div>
      <p style={{ color: "var(--gray-400)", fontSize: "0.875rem", marginBottom: "2rem" }}>Cross-project overview</p>

      <div className="stats-grid">
        <div className="stat-card"><div className="label">Projects</div><div className="value">{projects.length}</div></div>
        <div className="stat-card"><div className="label">Total Budget</div><div className="value">${totalBudget.toLocaleString()}</div></div>
        <div className="stat-card"><div className="label">Tasks Done</div><div className="value">{totalDone}/{totalTasks}</div></div>
        <div className="stat-card"><div className="label">Open Risks</div><div className="value" style={{ color: totalRisks > 0 ? "var(--danger)" : "var(--success)" }}>{totalRisks}</div></div>
      </div>

      <div className="card">
        <table>
          <thead>
            <tr><th>Project</th><th>Status</th><th>Approach</th><th>Budget</th><th>Progress</th><th>Risks</th></tr>
          </thead>
          <tbody>
            {projects.map((p: any) => (
              <tr key={p.id} style={{ cursor: "pointer" }} onClick={() => navigate(`/projects/${p.id}`)}>
                <td style={{ fontWeight: 500 }}>{p.name}</td>
                <td><span className="badge badge-blue">{p.status}</span></td>
                <td>{p.approach}</td>
                <td>${(p.budget || 0).toLocaleString()}</td>
                <td>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <div className="progress-bar" style={{ width: 80 }}>
                      <div className="fill" style={{ width: `${p.completion_pct}%` }} />
                    </div>
                    <span style={{ fontSize: "0.78rem", fontWeight: 600 }}>{p.completion_pct}%</span>
                  </div>
                </td>
                <td>
                  <span className={`badge ${p.open_risks > 0 ? "badge-red" : "badge-green"}`}>{p.open_risks}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
