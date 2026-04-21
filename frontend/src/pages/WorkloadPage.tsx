import { useParams } from "react-router-dom";
import { useGetWorkloadQuery } from "../services/api";

export default function WorkloadPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: workload = [], isLoading } = useGetWorkloadQuery(projectId!);

  if (isLoading) return <p style={{ color: "var(--gray-400)", padding: "2rem 0" }}>Loading...</p>;

  return (
    <div>
      <div style={{ marginBottom: "1.5rem" }}>
        <h2 style={{ fontSize: "1.4rem", fontWeight: 700, letterSpacing: "-0.02em", marginBottom: "0.3rem" }}>Resource Workload</h2>
        <p style={{ color: "var(--gray-400)", fontSize: "0.85rem" }}>Team member allocation and utilization</p>
      </div>

      {workload.length === 0 ? (
        <div className="empty-state"><p>Add team members and assign tasks to see workload.</p></div>
      ) : (
        <div className="card">
          <table>
            <thead>
              <tr><th>Member</th><th>Role</th><th>Availability</th><th>Active</th><th>Done</th><th>Remaining Hrs</th><th>Utilization</th></tr>
            </thead>
            <tbody>
              {workload.map((w: any) => (
                <tr key={w.id}>
                  <td style={{ fontWeight: 500 }}>{w.name}</td>
                  <td><span className="badge badge-blue">{w.role.replace(/_/g, " ")}</span></td>
                  <td>{w.availability}%</td>
                  <td>{w.active_tasks}</td>
                  <td>{w.done_tasks}</td>
                  <td>{w.remaining_hours}h</td>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <div className="progress-bar" style={{ width: 80 }}>
                        <div className="fill" style={{
                          width: `${Math.min(w.utilization, 100)}%`,
                          background: w.utilization > 100 ? "var(--danger)" : w.utilization > 80 ? "var(--warning)" : "var(--primary)",
                        }} />
                      </div>
                      <span style={{
                        fontSize: "0.78rem", fontWeight: 600,
                        color: w.utilization > 100 ? "var(--danger)" : w.utilization > 80 ? "var(--warning)" : "var(--gray-600)",
                      }}>
                        {w.utilization}%
                      </span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
