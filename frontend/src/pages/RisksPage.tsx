import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  useGetRisksQuery,
  useCreateRiskMutation,
  useUpdateRiskMutation,
  useDeleteRiskMutation,
} from "../services/api";

const CATEGORIES = ["technical", "external", "organizational", "project_management"];
const PROBABILITIES = ["very_low", "low", "medium", "high", "very_high"];
const IMPACTS = ["very_low", "low", "medium", "high", "very_high"];
const STRATEGIES = ["avoid", "mitigate", "transfer", "accept", "escalate", "exploit", "enhance", "share"];
const STATUSES = ["identified", "analyzing", "planned", "active", "resolved", "closed"];

const riskColor = (level: string) => {
  if (level.includes("high")) return "badge-red";
  if (level === "medium") return "badge-yellow";
  return "badge-green";
};

export default function RisksPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: risks = [] } = useGetRisksQuery(projectId!);
  const [create] = useCreateRiskMutation();
  const [update] = useUpdateRiskMutation();
  const [remove] = useDeleteRiskMutation();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    title: "", description: "", category: "technical", probability: "medium",
    impact: "medium", strategy: "mitigate", response_plan: "", trigger_conditions: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await create({ ...form, project_id: projectId });
    setForm({ title: "", description: "", category: "technical", probability: "medium", impact: "medium", strategy: "mitigate", response_plan: "", trigger_conditions: "" });
    setShowForm(false);
  };

  return (
    <div>
      <div className="card-header">
        <h2>Uncertainty Performance Domain</h2>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>+ Add Risk</button>
      </div>
      <p style={{ color: "var(--gray-500)", marginBottom: "1rem", fontSize: "0.9rem" }}>
        Identify, analyze, and respond to risks and uncertainty (PMBOK 2.8)
      </p>

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Add Risk</h3>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Title</label>
                <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
              </div>
              <div className="form-group">
                <label>Description</label>
                <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Category</label>
                  <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
                    {CATEGORIES.map((c) => <option key={c} value={c}>{c.replace(/_/g, " ")}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Strategy</label>
                  <select value={form.strategy} onChange={(e) => setForm({ ...form, strategy: e.target.value })}>
                    {STRATEGIES.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Probability</label>
                  <select value={form.probability} onChange={(e) => setForm({ ...form, probability: e.target.value })}>
                    {PROBABILITIES.map((p) => <option key={p} value={p}>{p.replace(/_/g, " ")}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Impact</label>
                  <select value={form.impact} onChange={(e) => setForm({ ...form, impact: e.target.value })}>
                    {IMPACTS.map((i) => <option key={i} value={i}>{i.replace(/_/g, " ")}</option>)}
                  </select>
                </div>
              </div>
              <div className="form-group">
                <label>Response Plan</label>
                <textarea value={form.response_plan} onChange={(e) => setForm({ ...form, response_plan: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Trigger Conditions</label>
                <textarea value={form.trigger_conditions} onChange={(e) => setForm({ ...form, trigger_conditions: e.target.value })} />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn" onClick={() => setShowForm(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Save</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {risks.length === 0 ? (
        <div className="empty-state"><p>No risks registered yet.</p></div>
      ) : (
        <div className="card">
          <table>
            <thead>
              <tr><th>Title</th><th>Category</th><th>Probability</th><th>Impact</th><th>Strategy</th><th>Status</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {risks.map((r: any) => (
                <tr key={r.id}>
                  <td>{r.title}</td>
                  <td><span className="badge badge-gray">{r.category?.replace(/_/g, " ")}</span></td>
                  <td><span className={`badge ${riskColor(r.probability)}`}>{r.probability?.replace(/_/g, " ")}</span></td>
                  <td><span className={`badge ${riskColor(r.impact)}`}>{r.impact?.replace(/_/g, " ")}</span></td>
                  <td>{r.strategy}</td>
                  <td>
                    <select
                      value={r.status}
                      onChange={(e) => update({ id: r.id, body: { status: e.target.value } })}
                      style={{ fontSize: "0.8rem", padding: "0.2rem" }}
                    >
                      {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </td>
                  <td><button className="btn btn-danger btn-sm" onClick={() => remove(r.id)}>Delete</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
