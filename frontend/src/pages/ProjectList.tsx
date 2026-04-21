import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useGetProjectsQuery, useCreateProjectMutation, useDeleteProjectMutation } from "../services/api";
import { useAppSelector, useAppDispatch } from "../app/hooks";
import { logout } from "../services/authSlice";

export default function ProjectList() {
  const { data: projects = [], isLoading } = useGetProjectsQuery();
  const [createProject] = useCreateProjectMutation();
  const [deleteProject] = useDeleteProjectMutation();
  const navigate = useNavigate();
  const user = useAppSelector((s) => s.auth.user);
  const dispatch = useAppDispatch();

  const handleLogout = () => {
    dispatch(logout());
    navigate("/login");
  };
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", development_approach: "predictive" });

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    await createProject(form);
    setForm({ name: "", description: "", development_approach: "predictive" });
    setShowForm(false);
  };

  if (isLoading) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh" }}>
      <p style={{ color: "var(--gray-400)" }}>Loading projects...</p>
    </div>
  );

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: "2.5rem 2rem" }}>
      {/* Top bar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.35rem" }}>
        <div>
          <h1 style={{ fontSize: "1.6rem", fontWeight: 700, letterSpacing: "-0.03em", color: "var(--gray-900)" }}>
            Projects
          </h1>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          {user && (
            <span style={{ fontSize: "0.82rem", color: "var(--gray-500)", fontWeight: 500, marginRight: "0.25rem" }}>
              {user.name}
            </span>
          )}
          <button className="btn" onClick={() => navigate("/portfolio")}>Portfolio</button>
          <button className="btn btn-primary" onClick={() => setShowForm(true)}>+ New Project</button>
          <button className="btn" onClick={handleLogout} style={{ color: "var(--gray-500)" }}>Sign out</button>
        </div>
      </div>
      <p style={{ color: "var(--gray-400)", marginBottom: "2rem", fontSize: "0.875rem" }}>
        PMBOK 7th Edition - 8 Performance Domains
      </p>

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Create Project</h3>
            <form onSubmit={handleCreate}>
              <div className="form-group">
                <label>Project Name</label>
                <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Website Redesign" required autoFocus />
              </div>
              <div className="form-group">
                <label>Description</label>
                <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Brief description of the project goals..." />
              </div>
              <div className="form-group">
                <label>Development Approach</label>
                <select value={form.development_approach} onChange={(e) => setForm({ ...form, development_approach: e.target.value })}>
                  <option value="predictive">Predictive</option>
                  <option value="adaptive">Adaptive</option>
                  <option value="hybrid">Hybrid</option>
                  <option value="agile">Agile</option>
                </select>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn" onClick={() => setShowForm(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Create Project</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {projects.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "4rem 2rem" }}>
          <div style={{ fontSize: "2.5rem", marginBottom: "0.75rem", opacity: 0.15 }}>&#9776;</div>
          <p style={{ color: "var(--gray-500)", fontSize: "0.95rem", marginBottom: "1rem" }}>No projects yet</p>
          <button className="btn btn-primary" onClick={() => setShowForm(true)}>Create your first project</button>
        </div>
      ) : (
        <div className="project-grid">
          {projects.map((p: any) => (
            <div key={p.id} className="project-card" onClick={() => navigate(`/projects/${p.id}`)}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.5rem" }}>
                <h3>{p.name}</h3>
                <span className="badge badge-blue">{p.status}</span>
              </div>
              <p style={{ fontSize: "0.835rem", color: "var(--gray-500)", marginBottom: "1rem", lineHeight: 1.5 }}>
                {p.description?.slice(0, 120) || "No description provided"}
              </p>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span className="badge badge-gray">{p.development_approach}</span>
                <button
                  className="btn btn-danger btn-sm"
                  onClick={(e) => { e.stopPropagation(); deleteProject(p.id); }}
                >
                  Remove
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
