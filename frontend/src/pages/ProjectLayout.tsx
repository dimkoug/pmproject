import { useState, useEffect } from "react";
import { NavLink, Outlet, useParams, useNavigate } from "react-router-dom";
import { useGetProjectQuery, useSearchQuery } from "../services/api";
import { useProjectWebSocket } from "../services/useWebSocket";
import { useAppSelector, useAppDispatch } from "../app/hooks";
import { logout } from "../services/authSlice";

export default function ProjectLayout() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: project } = useGetProjectQuery(projectId!);
  useProjectWebSocket(projectId);
  const wsConnected = useAppSelector((s) => s.ws.connected);
  const user = useAppSelector((s) => s.auth.user);
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const [darkMode, setDarkMode] = useState(localStorage.getItem("dark") === "1");
  const [searchQ, setSearchQ] = useState("");
  const { data: searchResults = [] } = useSearchQuery({ q: searchQ, projectId }, { skip: searchQ.length < 2 });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", darkMode ? "dark" : "light");
    localStorage.setItem("dark", darkMode ? "1" : "0");
  }, [darkMode]);

  const handleLogout = () => {
    dispatch(logout());
    navigate("/login");
  };

  const links = [
    { to: "", label: "Dashboard", end: true },
    { to: "tasks", label: "Tasks" },
    { to: "gantt", label: "Gantt Chart" },
    { to: "calendar", label: "Calendar" },
    { to: "schedule", label: "CPM / PERT" },
    { to: "sprints", label: "Sprints" },
    { to: "team", label: "Team" },
    { to: "workload", label: "Workload" },
    { to: "time-tracking", label: "Time Tracking" },
    { to: "stakeholders", label: "Stakeholders" },
    { to: "risks", label: "Risks" },
    { to: "deliverables", label: "Deliverables" },
    { to: "changes", label: "Changes" },
    { to: "evm", label: "EVM" },
    { to: "burndown", label: "Burndown" },
    { to: "monte-carlo", label: "Monte Carlo" },
    { to: "baselines", label: "Baselines" },
    { to: "measurements", label: "KPIs" },
    { to: "lessons", label: "Lessons Learned" },
    { to: "erp", label: "ERP / Finance" },
    { to: "crm", label: "CRM" },
    { to: "dms", label: "Documents" },
    { to: "admin", label: "Admin" },
    { to: "activity", label: "Activity Log" },
    { to: "reports", label: "Reports" },
  ];

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <h1>{project?.name || "Project"}</h1>
        <nav>
          <NavLink to="/" style={{ marginBottom: "0.25rem", borderBottom: "1px solid rgba(255,255,255,0.06)", paddingBottom: "0.65rem", fontSize: "0.78rem", opacity: 0.7 }}>
            &larr; All Projects
          </NavLink>
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === ""}
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          {/* Search */}
          <div style={{ position: "relative", marginBottom: "0.5rem" }}>
            <input
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              placeholder="Search..."
              style={{ width: "100%", padding: "0.4rem 0.6rem", background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 6, color: "#e2e8f0", fontSize: "0.78rem", outline: "none", fontFamily: "var(--font-sans)" }}
            />
            {searchQ.length >= 2 && searchResults.length > 0 && (
              <div style={{ position: "absolute", bottom: "100%", left: 0, right: 0, background: "#1e293b", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, maxHeight: 200, overflowY: "auto", marginBottom: 4, boxShadow: "0 -4px 12px rgba(0,0,0,0.3)" }}>
                {searchResults.map((r: any, i: number) => (
                  <div key={i} onClick={() => { setSearchQ(""); navigate(`/projects/${r.project_id}/tasks`); }}
                    style={{ padding: "0.4rem 0.65rem", cursor: "pointer", fontSize: "0.78rem", borderBottom: "1px solid rgba(255,255,255,0.05)", color: "#e2e8f0" }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.05)")}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                  >
                    <span style={{ fontSize: "0.65rem", color: "#818cf8", textTransform: "uppercase", marginRight: "0.35rem" }}>{r.type}</span>
                    {r.title}
                  </div>
                ))}
              </div>
            )}
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div className="ws-status">
              <span className={`ws-dot ${wsConnected ? "connected" : "disconnected"}`} />
              {wsConnected ? "Live" : "Reconnecting..."}
            </div>
            <button className="btn-logout" onClick={() => setDarkMode(!darkMode)} title="Toggle dark mode">
              {darkMode ? "Light" : "Dark"}
            </button>
          </div>
          {user && (
            <div className="sidebar-user">
              <span className="sidebar-user-name">{user.name}</span>
              <button className="btn-logout" onClick={handleLogout}>Logout</button>
            </div>
          )}
        </div>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
