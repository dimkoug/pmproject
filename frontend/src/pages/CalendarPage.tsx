import { useParams } from "react-router-dom";
import { useGetTasksQuery } from "../services/api";

export default function CalendarPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: tasks = [] } = useGetTasksQuery(projectId!);

  const tasksWithDates = tasks.filter((t: any) => t.start_date || t.due_date);
  const milestones = tasks.filter((t: any) => t.is_milestone);

  // Group by month
  const grouped: Record<string, any[]> = {};
  for (const t of tasksWithDates) {
    const d = t.start_date || t.due_date;
    const month = d.slice(0, 7);
    if (!grouped[month]) grouped[month] = [];
    grouped[month].push(t);
  }

  return (
    <div>
      <div style={{ marginBottom: "1.5rem" }}>
        <h2 style={{ fontSize: "1.4rem", fontWeight: 700, letterSpacing: "-0.02em", marginBottom: "0.3rem" }}>Calendar</h2>
        <p style={{ color: "var(--gray-400)", fontSize: "0.85rem" }}>Tasks and milestones timeline view</p>
      </div>

      {milestones.length > 0 && (
        <div className="card" style={{ marginBottom: "1.25rem" }}>
          <h3 style={{ marginBottom: "0.75rem" }}>Milestones</h3>
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            {milestones.map((t: any) => (
              <div key={t.id} style={{ padding: "0.5rem 1rem", background: "var(--primary-light)", borderRadius: "var(--radius)", borderLeft: "3px solid var(--primary)" }}>
                <div style={{ fontWeight: 600, fontSize: "0.85rem" }}>{t.title}</div>
                {t.due_date && <div style={{ fontSize: "0.75rem", color: "var(--gray-500)" }}>{t.due_date.slice(0, 10)}</div>}
              </div>
            ))}
          </div>
        </div>
      )}

      {Object.keys(grouped).length === 0 ? (
        <div className="empty-state"><p>Set start/due dates on tasks to see the calendar view.</p></div>
      ) : (
        Object.entries(grouped).sort().map(([month, monthTasks]) => (
          <div key={month} className="card" style={{ marginBottom: "1rem" }}>
            <h3 style={{ marginBottom: "0.75rem" }}>{new Date(month + "-01").toLocaleDateString("en-US", { year: "numeric", month: "long" })}</h3>
            <table>
              <thead><tr><th>Task</th><th>Start</th><th>Due</th><th>Status</th><th>Priority</th></tr></thead>
              <tbody>
                {monthTasks.map((t: any) => (
                  <tr key={t.id}>
                    <td style={{ fontWeight: 500 }}>{t.is_milestone ? "\u25C6 " : ""}{t.title}</td>
                    <td>{t.start_date?.slice(0, 10) || "-"}</td>
                    <td>{t.due_date?.slice(0, 10) || "-"}</td>
                    <td><span className="badge badge-blue">{t.status.replace(/_/g, " ")}</span></td>
                    <td><span className={`badge ${t.priority === "critical" ? "badge-red" : t.priority === "high" ? "badge-yellow" : "badge-gray"}`}>{t.priority}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))
      )}

      {/* All tasks without dates */}
      {tasks.filter((t: any) => !t.start_date && !t.due_date).length > 0 && (
        <div className="card">
          <h3 style={{ marginBottom: "0.75rem", color: "var(--gray-500)" }}>Unscheduled Tasks ({tasks.filter((t: any) => !t.start_date && !t.due_date).length})</h3>
          <div style={{ display: "flex", gap: "0.35rem", flexWrap: "wrap" }}>
            {tasks.filter((t: any) => !t.start_date && !t.due_date).map((t: any) => (
              <span key={t.id} className="badge badge-gray">{t.title}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
