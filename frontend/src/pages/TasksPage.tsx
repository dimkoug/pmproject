import { useState } from "react";
import { useParams } from "react-router-dom";
import Select from "react-select";
import BoardContainer from "../components/dnd/BoardContainer";
import BoardColumn from "../components/dnd/BoardColumn";
import DraggableCard from "../components/dnd/DraggableCard";
import {
  useGetTasksQuery,
  useCreateTaskMutation,
  useUpdateTaskMutation,
  useDeleteTaskMutation,
  useGetTeamMembersQuery,
  useGetDependenciesQuery,
  useCreateDependencyMutation,
  useDeleteDependencyMutation,
  useGetCpmQuery,
} from "../services/api";

const STATUSES = ["backlog", "todo", "in_progress", "in_review", "done", "blocked"];
const PRIORITIES = ["critical", "high", "medium", "low"];
const COLUMNS = ["backlog", "todo", "in_progress", "in_review", "done"];

const priorityColor = (p: string) => {
  if (p === "critical") return "badge-red";
  if (p === "high") return "badge-yellow";
  return "badge-gray";
};

const emptyForm = {
  title: "", description: "", status: "backlog", priority: "medium",
  story_points: "", assignee_id: "",
  duration_days: "", optimistic_duration: "", most_likely_duration: "", pessimistic_duration: "",
};

export default function TasksPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: tasks = [] } = useGetTasksQuery(projectId!);
  const { data: members = [] } = useGetTeamMembersQuery(projectId!);
  const { data: deps = [] } = useGetDependenciesQuery(projectId!);
  const { data: cpm } = useGetCpmQuery(projectId!);
  const [create] = useCreateTaskMutation();
  const [updateTask] = useUpdateTaskMutation();
  const [remove] = useDeleteTaskMutation();
  const [createDep] = useCreateDependencyMutation();
  const [deleteDep] = useDeleteDependencyMutation();
  const [showForm, setShowForm] = useState(false);
  const [editTask, setEditTask] = useState<any>(null);
  const [view, setView] = useState<"board" | "list">("board");
  const [form, setForm] = useState(emptyForm);
  const [addPredId, setAddPredId] = useState("");
  const [addDepType, setAddDepType] = useState("finish_to_start");
  const [addLag, setAddLag] = useState(0);
  const [depError, setDepError] = useState("");

  const numOrNull = (v: string) => (v ? +v : null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await create({
      ...form,
      project_id: projectId,
      story_points: numOrNull(form.story_points),
      duration_days: numOrNull(form.duration_days),
      optimistic_duration: numOrNull(form.optimistic_duration),
      most_likely_duration: numOrNull(form.most_likely_duration),
      pessimistic_duration: numOrNull(form.pessimistic_duration),
      assignee_id: form.assignee_id || null,
    });
    setForm(emptyForm);
    setShowForm(false);
  };

  const openEdit = (t: any) => {
    setEditTask({ ...t });
    setAddPredId("");
    setAddDepType("finish_to_start");
    setAddLag(0);
    setDepError("");
  };

  const handleEditSave = async () => {
    if (!editTask) return;
    await updateTask({
      id: editTask.id,
      body: {
        title: editTask.title,
        description: editTask.description,
        status: editTask.status,
        priority: editTask.priority,
        story_points: editTask.story_points || null,
        duration_days: editTask.duration_days || null,
        optimistic_duration: editTask.optimistic_duration || null,
        most_likely_duration: editTask.most_likely_duration || null,
        pessimistic_duration: editTask.pessimistic_duration || null,
        assignee_id: editTask.assignee_id || null,
      },
    });
    setEditTask(null);
  };

  const handleAddPredecessor = async () => {
    if (!addPredId || !editTask) return;
    setDepError("");
    try {
      await createDep({
        project_id: projectId,
        predecessor_id: addPredId,
        successor_id: editTask.id,
        dependency_type: addDepType,
        lag_days: addLag,
      }).unwrap();
      setAddPredId("");
      setAddDepType("finish_to_start");
      setAddLag(0);
    } catch (err: any) {
      setDepError(err?.data?.detail || "Failed to add dependency");
    }
  };

  const getPredecessors = (taskId: string) =>
    deps.filter((d: any) => d.successor_id === taskId);
  const getSuccessors = (taskId: string) =>
    deps.filter((d: any) => d.predecessor_id === taskId);
  const taskName = (id: string) => tasks.find((t: any) => t.id === id)?.title || "Unknown";

  // CPM lookup: is this task on the critical path?
  const cpmTask = (taskId: string) => cpm?.tasks?.find((t: any) => t.id === taskId);
  const isCritical = (taskId: string) => cpmTask(taskId)?.is_critical;

  // Already a predecessor of this task?
  const isAlreadyPredecessor = (predId: string, taskId: string) =>
    deps.some((d: any) => d.predecessor_id === predId && d.successor_id === taskId);

  return (
    <div>
      <div className="card-header">
        <h2>Project Work Performance Domain</h2>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button className={`btn ${view === "board" ? "btn-primary" : ""}`} onClick={() => setView("board")}>Board</button>
          <button className={`btn ${view === "list" ? "btn-primary" : ""}`} onClick={() => setView("list")}>List</button>
          <button className="btn btn-primary" onClick={() => setShowForm(true)}>+ Add Task</button>
        </div>
      </div>

      {/* Auto-calculated CPM summary */}
      {cpm && cpm.project_duration > 0 && (
        <div className="stats-grid" style={{ marginBottom: "1rem" }}>
          <div className="stat-card">
            <div className="label">Project Duration</div>
            <div className="value">{cpm.project_duration}d</div>
          </div>
          <div className="stat-card">
            <div className="label">Critical Path Tasks</div>
            <div className="value">{cpm.critical_path.length}</div>
          </div>
          <div className="stat-card">
            <div className="label">Total Tasks</div>
            <div className="value">{tasks.length}</div>
          </div>
        </div>
      )}

      {/* ── Create Task Modal ──────────────────── */}
      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Create Task</h3>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Title</label>
                <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required autoFocus />
              </div>
              <div className="form-group">
                <label>Description</label>
                <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Status</label>
                  <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                    {STATUSES.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Priority</label>
                  <select value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}>
                    {PRIORITIES.map((p) => <option key={p} value={p}>{p}</option>)}
                  </select>
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Story Points</label>
                  <input type="number" value={form.story_points} onChange={(e) => setForm({ ...form, story_points: e.target.value })} />
                </div>
                <div className="form-group">
                  <label>Assignee</label>
                  <select value={form.assignee_id} onChange={(e) => setForm({ ...form, assignee_id: e.target.value })}>
                    <option value="">Unassigned</option>
                    {members.map((m: any) => <option key={m.id} value={m.id}>{m.name}</option>)}
                  </select>
                </div>
              </div>

              <div style={{ borderTop: "1px solid var(--gray-100)", marginTop: "0.75rem", paddingTop: "0.75rem" }}>
                <p style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--gray-700)", marginBottom: "0.25rem" }}>Duration Estimates</p>
                <p style={{ fontSize: "0.78rem", color: "var(--gray-400)", marginBottom: "0.75rem" }}>
                  Enter duration, or 3-point estimates for PERT analysis. CPM/PERT are calculated automatically.
                </p>
                <div className="form-group">
                  <label>Duration (days)</label>
                  <input type="number" step="0.5" min="0" value={form.duration_days} onChange={(e) => setForm({ ...form, duration_days: e.target.value })} placeholder="How many days will this take?" />
                </div>
                <div style={{ display: "flex", gap: "0.75rem" }}>
                  <div className="form-group" style={{ flex: 1 }}>
                    <label>Best case (O)</label>
                    <input type="number" step="0.5" min="0" value={form.optimistic_duration} onChange={(e) => setForm({ ...form, optimistic_duration: e.target.value })} placeholder="Min" />
                  </div>
                  <div className="form-group" style={{ flex: 1 }}>
                    <label>Expected (M)</label>
                    <input type="number" step="0.5" min="0" value={form.most_likely_duration} onChange={(e) => setForm({ ...form, most_likely_duration: e.target.value })} placeholder="Likely" />
                  </div>
                  <div className="form-group" style={{ flex: 1 }}>
                    <label>Worst case (P)</label>
                    <input type="number" step="0.5" min="0" value={form.pessimistic_duration} onChange={(e) => setForm({ ...form, pessimistic_duration: e.target.value })} placeholder="Max" />
                  </div>
                </div>
              </div>

              <div className="modal-actions">
                <button type="button" className="btn" onClick={() => setShowForm(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Create</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Edit Task Modal (simple) ──────────── */}
      {editTask && (
        <div className="modal-overlay" onClick={() => setEditTask(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 640 }}>
            <h3>
              Edit Task
              {isCritical(editTask.id) && <span className="badge badge-red" style={{ marginLeft: "0.5rem", verticalAlign: "middle" }}>Critical Path</span>}
            </h3>

            <div className="form-group">
              <label>Title</label>
              <input value={editTask.title} onChange={(e) => setEditTask({ ...editTask, title: e.target.value })} />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Status</label>
                <select value={editTask.status} onChange={(e) => setEditTask({ ...editTask, status: e.target.value })}>
                  {STATUSES.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Priority</label>
                <select value={editTask.priority} onChange={(e) => setEditTask({ ...editTask, priority: e.target.value })}>
                  {PRIORITIES.map((p) => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Story Points</label>
                <input type="number" value={editTask.story_points || ""} onChange={(e) => setEditTask({ ...editTask, story_points: e.target.value ? +e.target.value : null })} />
              </div>
              <div className="form-group">
                <label>Assignee</label>
                <select value={editTask.assignee_id || ""} onChange={(e) => setEditTask({ ...editTask, assignee_id: e.target.value || null })}>
                  <option value="">Unassigned</option>
                  {members.map((m: any) => <option key={m.id} value={m.id}>{m.name}</option>)}
                </select>
              </div>
            </div>

            {/* Duration */}
            <div style={{ borderTop: "1px solid var(--gray-100)", marginTop: "0.5rem", paddingTop: "0.75rem" }}>
              <p style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--gray-700)", marginBottom: "0.75rem" }}>Duration Estimates</p>
              <div className="form-group">
                <label>Duration (days)</label>
                <input type="number" step="0.5" min="0" value={editTask.duration_days || ""} onChange={(e) => setEditTask({ ...editTask, duration_days: e.target.value ? +e.target.value : null })} />
              </div>
              <div style={{ display: "flex", gap: "0.75rem" }}>
                <div className="form-group" style={{ flex: 1 }}>
                  <label>Best case (O)</label>
                  <input type="number" step="0.5" min="0" value={editTask.optimistic_duration || ""} onChange={(e) => setEditTask({ ...editTask, optimistic_duration: e.target.value ? +e.target.value : null })} />
                </div>
                <div className="form-group" style={{ flex: 1 }}>
                  <label>Expected (M)</label>
                  <input type="number" step="0.5" min="0" value={editTask.most_likely_duration || ""} onChange={(e) => setEditTask({ ...editTask, most_likely_duration: e.target.value ? +e.target.value : null })} />
                </div>
                <div className="form-group" style={{ flex: 1 }}>
                  <label>Worst case (P)</label>
                  <input type="number" step="0.5" min="0" value={editTask.pessimistic_duration || ""} onChange={(e) => setEditTask({ ...editTask, pessimistic_duration: e.target.value ? +e.target.value : null })} />
                </div>
              </div>

              {/* Auto-calculated PERT result */}
              {editTask.optimistic_duration && editTask.most_likely_duration && editTask.pessimistic_duration && (
                <div style={{ background: "var(--primary-light)", borderRadius: "var(--radius)", padding: "0.65rem 0.85rem", fontSize: "0.82rem", color: "var(--primary)", marginTop: "-0.25rem" }}>
                  PERT Expected: <strong>{((editTask.optimistic_duration + 4 * editTask.most_likely_duration + editTask.pessimistic_duration) / 6).toFixed(1)} days</strong>
                  &nbsp;&middot;&nbsp;
                  Std Dev: <strong>{((editTask.pessimistic_duration - editTask.optimistic_duration) / 6).toFixed(2)}</strong>
                </div>
              )}
            </div>

            {/* Predecessors */}
            <div style={{ borderTop: "1px solid var(--gray-100)", marginTop: "0.75rem", paddingTop: "0.75rem" }}>
              <p style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--gray-700)", marginBottom: "0.5rem" }}>
                Predecessors
              </p>

              {getPredecessors(editTask.id).length > 0 ? (
                <table style={{ marginBottom: "0.75rem", fontSize: "0.835rem" }}>
                  <thead>
                    <tr>
                      <th style={{ fontSize: "0.7rem" }}>Task</th>
                      <th style={{ fontSize: "0.7rem" }}>Type</th>
                      <th style={{ fontSize: "0.7rem" }}>Lag</th>
                      <th style={{ fontSize: "0.7rem", width: 50 }}></th>
                    </tr>
                  </thead>
                  <tbody>
                    {getPredecessors(editTask.id).map((d: any) => {
                      const typeLabels: Record<string, string> = {
                        finish_to_start: "FS", finish_to_finish: "FF",
                        start_to_start: "SS", start_to_finish: "SF",
                      };
                      return (
                        <tr key={d.id}>
                          <td>{taskName(d.predecessor_id)}</td>
                          <td><span className="badge badge-blue">{typeLabels[d.dependency_type] || d.dependency_type}</span></td>
                          <td>{d.lag_days !== 0 ? `${d.lag_days > 0 ? "+" : ""}${d.lag_days}d` : "-"}</td>
                          <td>
                            <button className="btn btn-danger btn-sm" onClick={() => deleteDep({ projectId: projectId!, depId: d.id })}>
                              &times;
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              ) : (
                <p style={{ fontSize: "0.82rem", color: "var(--gray-400)", marginBottom: "0.65rem" }}>
                  No predecessors - this task can start immediately
                </p>
              )}

              {depError && (
                <div className="auth-error" style={{ marginBottom: "0.65rem" }}>{depError}</div>
              )}

              <div style={{ display: "flex", gap: "0.5rem", alignItems: "flex-end", flexWrap: "wrap" }}>
                <div style={{ flex: "1 1 150px", minWidth: 0 }}>
                  <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 600, color: "var(--gray-600)", marginBottom: "0.2rem" }}>Task</label>
                  <Select
                    value={addPredId ? {
                      value: addPredId,
                      label: tasks.find((t: any) => t.id === addPredId)?.title || addPredId,
                    } : null}
                    onChange={(opt) => setAddPredId(opt?.value || "")}
                    options={tasks
                      .filter((t: any) => t.id !== editTask.id && !isAlreadyPredecessor(t.id, editTask.id))
                      .map((t: any) => ({
                        value: t.id,
                        label: `${t.title}${t.duration_days ? ` (${t.duration_days}d)` : ""}`,
                      }))}
                    placeholder="Search predecessor..."
                    isClearable
                    menuPortalTarget={document.body}
                    styles={{
                      control: (base) => ({
                        ...base,
                        minHeight: 34,
                        fontSize: "0.835rem",
                        borderColor: "var(--gray-300)",
                        borderRadius: 8,
                        boxShadow: "none",
                        "&:hover": { borderColor: "var(--gray-400)" },
                      }),
                      option: (base, state) => ({
                        ...base,
                        fontSize: "0.835rem",
                        backgroundColor: state.isFocused ? "var(--primary-light)" : "white",
                        color: "var(--gray-800)",
                        "&:active": { backgroundColor: "var(--primary-50)" },
                      }),
                      placeholder: (base) => ({ ...base, color: "var(--gray-400)", fontSize: "0.835rem" }),
                      singleValue: (base) => ({ ...base, fontSize: "0.835rem" }),
                      menuPortal: (base) => ({ ...base, zIndex: 9999 }),
                      menu: (base) => ({ ...base, borderRadius: 8, boxShadow: "0 4px 12px rgba(0,0,0,0.12)" }),
                      input: (base) => ({ ...base, fontSize: "0.835rem" }),
                    }}
                  />
                </div>
                <div style={{ flex: "0 0 100px" }}>
                  <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 600, color: "var(--gray-600)", marginBottom: "0.2rem" }}>Type</label>
                  <select
                    value={addDepType}
                    onChange={(e) => setAddDepType(e.target.value)}
                    style={{ width: "100%", padding: "0.45rem 0.4rem", border: "1px solid var(--gray-300)", borderRadius: "var(--radius)", fontSize: "0.835rem", fontFamily: "var(--font-sans)" }}
                  >
                    <option value="finish_to_start">FS</option>
                    <option value="start_to_start">SS</option>
                    <option value="finish_to_finish">FF</option>
                    <option value="start_to_finish">SF</option>
                  </select>
                </div>
                <div style={{ flex: "0 0 70px" }}>
                  <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 600, color: "var(--gray-600)", marginBottom: "0.2rem" }}>Lag (days)</label>
                  <input
                    type="number"
                    value={addLag}
                    onChange={(e) => setAddLag(+e.target.value)}
                    style={{ width: "100%", padding: "0.45rem 0.5rem", border: "1px solid var(--gray-300)", borderRadius: "var(--radius)", fontSize: "0.835rem", fontFamily: "var(--font-sans)" }}
                  />
                </div>
                <button
                  className="btn btn-primary btn-sm"
                  style={{ padding: "0.47rem 0.85rem", marginBottom: "1px" }}
                  onClick={handleAddPredecessor}
                  disabled={!addPredId}
                >
                  Add
                </button>
              </div>
              <p style={{ fontSize: "0.72rem", color: "var(--gray-400)", marginTop: "0.4rem" }}>
                FS = Finish-to-Start &middot; SS = Start-to-Start &middot; FF = Finish-to-Finish &middot; SF = Start-to-Finish &middot; Lag: positive = delay, negative = lead
              </p>
            </div>

            {/* Successors (read-only) */}
            {getSuccessors(editTask.id).length > 0 && (
              <div style={{ borderTop: "1px solid var(--gray-100)", marginTop: "0.75rem", paddingTop: "0.75rem" }}>
                <p style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--gray-700)", marginBottom: "0.5rem" }}>
                  Blocks these tasks
                </p>
                <div style={{ display: "flex", gap: "0.35rem", flexWrap: "wrap" }}>
                  {getSuccessors(editTask.id).map((d: any) => (
                    <span key={d.id} className="badge badge-gray" style={{ padding: "0.3rem 0.7rem" }}>
                      {taskName(d.successor_id)}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Auto-calculated schedule info from CPM */}
            {cpmTask(editTask.id) && cpmTask(editTask.id).duration > 0 && (
              <div style={{ borderTop: "1px solid var(--gray-100)", marginTop: "0.75rem", paddingTop: "0.75rem" }}>
                <p style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--gray-700)", marginBottom: "0.5rem" }}>
                  Auto-Calculated Schedule
                </p>
                <div style={{ display: "flex", gap: "1.5rem", fontSize: "0.82rem", color: "var(--gray-600)", flexWrap: "wrap" }}>
                  <span>Early Start: <strong>Day {cpmTask(editTask.id).es}</strong></span>
                  <span>Early Finish: <strong>Day {cpmTask(editTask.id).ef}</strong></span>
                  <span>Late Start: <strong>Day {cpmTask(editTask.id).ls}</strong></span>
                  <span>Late Finish: <strong>Day {cpmTask(editTask.id).lf}</strong></span>
                  <span>Float: <strong style={{ color: cpmTask(editTask.id).total_float === 0 ? "var(--danger)" : "var(--success)" }}>{cpmTask(editTask.id).total_float} days</strong></span>
                </div>
              </div>
            )}

            <div className="modal-actions">
              <button type="button" className="btn" onClick={() => setEditTask(null)}>Cancel</button>
              <button type="button" className="btn btn-primary" onClick={handleEditSave}>Save Changes</button>
            </div>
          </div>
        </div>
      )}

      {/* ── Board View (Drag-and-Drop) ─────────── */}
      {view === "board" ? (
        <BoardContainer
          onDragEnd={(itemId, newCol) => updateTask({ id: itemId, body: { status: newCol } })}
          renderOverlay={(activeId) => {
            const t = tasks.find((x: any) => x.id === activeId);
            return t ? <div className="board-card" style={{ opacity: 0.9, boxShadow: "0 8px 24px rgba(0,0,0,0.15)", width: 250 }}><div className="title">{t.title}</div></div> : null;
          }}
        >
        <div className="board">
          {COLUMNS.map((col) => (
            <BoardColumn key={col} id={col} title={col.replace(/_/g, " ")} count={tasks.filter((t: any) => t.status === col).length}>
              {tasks
                .filter((t: any) => t.status === col)
                .map((t: any) => (
                  <DraggableCard
                    key={t.id}
                    id={t.id}
                    onClick={() => openEdit(t)}
                    style={isCritical(t.id) ? { borderLeft: "3px solid var(--danger)" } : undefined}
                  >
                    <div className="title">{t.title}</div>
                    <div className="meta" style={{ display: "flex", gap: "0.35rem", alignItems: "center", flexWrap: "wrap" }}>
                      <span className={`badge ${priorityColor(t.priority)}`}>{t.priority}</span>
                      {t.duration_days && <span className="badge badge-blue">{t.duration_days}d</span>}
                      {isCritical(t.id) && <span className="badge badge-red">critical</span>}
                      {getPredecessors(t.id).length > 0 && (
                        <span className="badge badge-yellow">{getPredecessors(t.id).length} dep</span>
                      )}
                    </div>
                  </DraggableCard>
                ))}
            </BoardColumn>
          ))}
        </div>
        </BoardContainer>
      ) : (
        /* ── List View ────────────────────────── */
        <div className="card">
          <div style={{ overflowX: "auto" }}>
            <table>
              <thead>
                <tr>
                  <th>Title</th><th>Status</th><th>Priority</th><th>Duration</th>
                  <th>Predecessors</th><th>Float</th><th>Critical</th><th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((t: any) => {
                  const ct = cpmTask(t.id);
                  return (
                    <tr key={t.id} style={{ cursor: "pointer" }} onClick={() => openEdit(t)}>
                      <td style={{ fontWeight: 500 }}>{t.title}</td>
                      <td><span className="badge badge-blue">{t.status?.replace(/_/g, " ")}</span></td>
                      <td><span className={`badge ${priorityColor(t.priority)}`}>{t.priority}</span></td>
                      <td>{t.duration_days ? `${t.duration_days}d` : "-"}</td>
                      <td>
                        {getPredecessors(t.id).length > 0 ? (
                          <div style={{ display: "flex", gap: "0.25rem", flexWrap: "wrap" }}>
                            {getPredecessors(t.id).map((d: any) => {
                              const typeLabels: Record<string, string> = {
                                finish_to_start: "FS", finish_to_finish: "FF",
                                start_to_start: "SS", start_to_finish: "SF",
                              };
                              const lag = d.lag_days !== 0 ? (d.lag_days > 0 ? `+${d.lag_days}d` : `${d.lag_days}d`) : "";
                              return (
                                <span key={d.id} className="badge badge-yellow" style={{ fontSize: "0.7rem" }}>
                                  {taskName(d.predecessor_id)} {typeLabels[d.dependency_type] || "FS"}{lag && ` ${lag}`}
                                </span>
                              );
                            })}
                          </div>
                        ) : <span style={{ color: "var(--gray-400)" }}>-</span>}
                      </td>
                      <td>
                        {ct && ct.duration > 0 ? (
                          <span className={`badge ${ct.total_float === 0 ? "badge-red" : "badge-green"}`}>{ct.total_float}d</span>
                        ) : "-"}
                      </td>
                      <td>
                        {ct?.is_critical ? <span className="badge badge-red">Yes</span> : "-"}
                      </td>
                      <td onClick={(e) => e.stopPropagation()}>
                        <button className="btn btn-danger btn-sm" onClick={() => remove(t.id)}>Delete</button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
