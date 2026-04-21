import { useParams } from "react-router-dom";
import { useGetGanttQuery } from "../services/api";

const STATUS_COLORS: Record<string, string> = {
  done: "var(--success)", in_progress: "var(--primary)", in_review: "var(--warning)",
  todo: "var(--gray-400)", backlog: "var(--gray-300)", blocked: "var(--danger)",
};

export default function GanttPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: gantt, isLoading } = useGetGanttQuery(projectId!);

  if (isLoading) return <p style={{ color: "var(--gray-400)", padding: "2rem 0" }}>Loading...</p>;

  const bars = gantt?.bars || [];
  const duration = gantt?.project_duration || 1;
  const colWidth = Math.max(30, Math.min(60, 800 / duration));

  return (
    <div>
      <div style={{ marginBottom: "1.5rem" }}>
        <h2 style={{ fontSize: "1.4rem", fontWeight: 700, letterSpacing: "-0.02em", marginBottom: "0.3rem" }}>Gantt Chart</h2>
        <p style={{ color: "var(--gray-400)", fontSize: "0.85rem" }}>
          Visual project timeline &middot; {duration} days total &middot; {bars.filter((b: any) => b.is_critical).length} critical tasks
        </p>
      </div>

      {bars.length === 0 ? (
        <div className="empty-state"><p>Add tasks with durations and dependencies to see the Gantt chart.</p></div>
      ) : (
        <div className="card" style={{ overflowX: "auto", padding: "1rem" }}>
          {/* Day headers */}
          <div style={{ display: "flex", marginLeft: 220, marginBottom: "0.25rem" }}>
            {Array.from({ length: Math.ceil(duration) }, (_, i) => (
              <div key={i} style={{ width: colWidth, textAlign: "center", fontSize: "0.65rem", color: "var(--gray-400)", flexShrink: 0 }}>
                {i + 1}
              </div>
            ))}
          </div>

          {/* Bars */}
          {bars.map((bar: any) => (
            <div key={bar.id} style={{ display: "flex", alignItems: "center", height: 32, marginBottom: 2 }}>
              {/* Label */}
              <div style={{
                width: 220, flexShrink: 0, fontSize: "0.78rem", fontWeight: bar.is_critical ? 600 : 400,
                color: bar.is_critical ? "var(--danger)" : "var(--gray-700)",
                overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", paddingRight: "0.5rem",
              }}>
                {bar.is_milestone ? "\u25C6 " : ""}{bar.wbs_code ? `${bar.wbs_code} ` : ""}{bar.title}
              </div>
              {/* Timeline area */}
              <div style={{ position: "relative", flex: 1, height: "100%", background: "var(--gray-50)", borderRadius: 4 }}>
                {bar.is_milestone ? (
                  <div style={{
                    position: "absolute", left: `${(bar.start_day / duration) * 100}%`, top: "50%",
                    width: 12, height: 12, background: "var(--primary)", transform: "translate(-50%, -50%) rotate(45deg)",
                  }} />
                ) : (
                  <div style={{
                    position: "absolute",
                    left: `${(bar.start_day / duration) * 100}%`,
                    width: `${Math.max(((bar.end_day - bar.start_day) / duration) * 100, 1)}%`,
                    height: 20, top: 6,
                    background: bar.is_critical ? "var(--danger)" : (STATUS_COLORS[bar.status] || "var(--gray-400)"),
                    borderRadius: 4, opacity: 0.85,
                    display: "flex", alignItems: "center", paddingLeft: 4,
                  }}>
                    {/* Progress fill */}
                    <div style={{
                      position: "absolute", left: 0, top: 0, height: "100%", borderRadius: 4,
                      width: `${bar.progress}%`, background: "rgba(0,0,0,0.15)",
                    }} />
                    <span style={{ fontSize: "0.6rem", color: "white", fontWeight: 600, position: "relative", zIndex: 1 }}>
                      {bar.duration > 0 ? `${bar.duration}d` : ""}
                    </span>
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Legend */}
          <div style={{ display: "flex", gap: "1rem", marginTop: "1rem", paddingLeft: 220, fontSize: "0.72rem", color: "var(--gray-500)" }}>
            <span><span style={{ display: "inline-block", width: 10, height: 10, background: "var(--danger)", borderRadius: 2, marginRight: 4 }} />Critical</span>
            <span><span style={{ display: "inline-block", width: 10, height: 10, background: "var(--primary)", borderRadius: 2, marginRight: 4 }} />In Progress</span>
            <span><span style={{ display: "inline-block", width: 10, height: 10, background: "var(--success)", borderRadius: 2, marginRight: 4 }} />Done</span>
            <span><span style={{ display: "inline-block", width: 10, height: 10, background: "var(--gray-400)", borderRadius: 2, marginRight: 4 }} />Other</span>
          </div>
        </div>
      )}
    </div>
  );
}
