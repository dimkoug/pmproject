import { useState } from "react";
import { useParams } from "react-router-dom";
import { useGetLessonsQuery, useCreateLessonMutation, useDeleteLessonMutation } from "../services/api";

const CATEGORIES = ["process", "technical", "team", "communication", "risk", "stakeholder", "other"];

export default function LessonsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: lessons = [], refetch } = useGetLessonsQuery(projectId!);
  const [create] = useCreateLessonMutation();
  const [remove] = useDeleteLessonMutation();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ title: "", category: "other", what_happened: "", impact: "", recommendation: "" });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await create({ ...form, project_id: projectId });
    setForm({ title: "", category: "other", what_happened: "", impact: "", recommendation: "" });
    setShowForm(false);
    refetch();
  };

  return (
    <div>
      <div className="card-header">
        <h2>Lessons Learned</h2>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>+ Add Lesson</button>
      </div>
      <p style={{ color: "var(--gray-400)", fontSize: "0.85rem", marginBottom: "1rem" }}>
        Capture knowledge for future projects (PMBOK knowledge management)
      </p>

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Record Lesson Learned</h3>
            <form onSubmit={handleSubmit}>
              <div className="form-row">
                <div className="form-group"><label>Title</label><input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required autoFocus /></div>
                <div className="form-group"><label>Category</label>
                  <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
                    {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
              </div>
              <div className="form-group"><label>What happened?</label><textarea value={form.what_happened} onChange={(e) => setForm({ ...form, what_happened: e.target.value })} required /></div>
              <div className="form-group"><label>Impact</label><textarea value={form.impact} onChange={(e) => setForm({ ...form, impact: e.target.value })} /></div>
              <div className="form-group"><label>Recommendation</label><textarea value={form.recommendation} onChange={(e) => setForm({ ...form, recommendation: e.target.value })} /></div>
              <div className="modal-actions">
                <button type="button" className="btn" onClick={() => setShowForm(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Save</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {lessons.length === 0 ? (
        <div className="empty-state"><p>No lessons recorded yet.</p></div>
      ) : (
        <div>
          {lessons.map((l: any) => (
            <div key={l.id} className="card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.5rem" }}>
                <div>
                  <h3 style={{ fontSize: "1rem", fontWeight: 600 }}>{l.title}</h3>
                  <span className="badge badge-blue" style={{ marginTop: "0.25rem" }}>{l.category}</span>
                </div>
                <button className="btn btn-danger btn-sm" onClick={() => { remove(l.id); refetch(); }}>Delete</button>
              </div>
              <div style={{ fontSize: "0.85rem", color: "var(--gray-700)" }}>
                <p style={{ marginBottom: "0.5rem" }}><strong>What happened:</strong> {l.what_happened}</p>
                {l.impact && <p style={{ marginBottom: "0.5rem" }}><strong>Impact:</strong> {l.impact}</p>}
                {l.recommendation && <p><strong>Recommendation:</strong> {l.recommendation}</p>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
