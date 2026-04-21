import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  useGetMeasurementsQuery,
  useCreateMeasurementMutation,
  useUpdateMeasurementMutation,
  useDeleteMeasurementMutation,
} from "../services/api";

const METRIC_TYPES = ["kpi", "leading", "lagging", "outcome"];
const DOMAINS = ["schedule", "cost", "quality", "scope", "risk", "stakeholder", "team", "value"];

export default function MeasurementsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: measurements = [] } = useGetMeasurementsQuery(projectId!);
  const [create] = useCreateMeasurementMutation();
  const [update] = useUpdateMeasurementMutation();
  const [remove] = useDeleteMeasurementMutation();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    name: "", description: "", metric_type: "kpi", domain: "value",
    target_value: "", actual_value: "", unit: "",
    threshold_red: "", threshold_yellow: "", threshold_green: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await create({
      ...form,
      project_id: projectId,
      target_value: form.target_value ? +form.target_value : null,
      actual_value: form.actual_value ? +form.actual_value : null,
      threshold_red: form.threshold_red ? +form.threshold_red : null,
      threshold_yellow: form.threshold_yellow ? +form.threshold_yellow : null,
      threshold_green: form.threshold_green ? +form.threshold_green : null,
    });
    setForm({ name: "", description: "", metric_type: "kpi", domain: "value", target_value: "", actual_value: "", unit: "", threshold_red: "", threshold_yellow: "", threshold_green: "" });
    setShowForm(false);
  };

  const getHealthColor = (m: any) => {
    if (m.actual_value == null || m.target_value == null) return "";
    const ratio = m.actual_value / m.target_value;
    if (ratio >= 0.9) return "badge-green";
    if (ratio >= 0.7) return "badge-yellow";
    return "badge-red";
  };

  return (
    <div>
      <div className="card-header">
        <h2>Measurement Performance Domain</h2>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>+ Add Measurement</button>
      </div>
      <p style={{ color: "var(--gray-500)", marginBottom: "1rem", fontSize: "0.9rem" }}>
        Establish effective measures and KPIs to assess project performance (PMBOK 2.7)
      </p>

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Add Measurement</h3>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Name</label>
                <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
              </div>
              <div className="form-group">
                <label>Description</label>
                <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Type</label>
                  <select value={form.metric_type} onChange={(e) => setForm({ ...form, metric_type: e.target.value })}>
                    {METRIC_TYPES.map((t) => <option key={t} value={t}>{t.toUpperCase()}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Domain</label>
                  <select value={form.domain} onChange={(e) => setForm({ ...form, domain: e.target.value })}>
                    {DOMAINS.map((d) => <option key={d} value={d}>{d}</option>)}
                  </select>
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Target Value</label>
                  <input type="number" value={form.target_value} onChange={(e) => setForm({ ...form, target_value: e.target.value })} />
                </div>
                <div className="form-group">
                  <label>Actual Value</label>
                  <input type="number" value={form.actual_value} onChange={(e) => setForm({ ...form, actual_value: e.target.value })} />
                </div>
              </div>
              <div className="form-group">
                <label>Unit</label>
                <input value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} placeholder="e.g., %, hours, $" />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn" onClick={() => setShowForm(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Save</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {measurements.length === 0 ? (
        <div className="empty-state"><p>No measurements configured yet.</p></div>
      ) : (
        <div className="card">
          <table>
            <thead>
              <tr><th>Name</th><th>Type</th><th>Domain</th><th>Target</th><th>Actual</th><th>Unit</th><th>Health</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {measurements.map((m: any) => (
                <tr key={m.id}>
                  <td>{m.name}</td>
                  <td><span className="badge badge-gray">{m.metric_type?.toUpperCase()}</span></td>
                  <td><span className="badge badge-blue">{m.domain}</span></td>
                  <td>{m.target_value ?? "-"}</td>
                  <td>
                    <input
                      type="number"
                      value={m.actual_value ?? ""}
                      onChange={(e) => update({ id: m.id, body: { actual_value: e.target.value ? +e.target.value : null } })}
                      style={{ width: 70, fontSize: "0.8rem", padding: "0.15rem" }}
                    />
                  </td>
                  <td>{m.unit || "-"}</td>
                  <td><span className={`badge ${getHealthColor(m)}`}>
                    {m.actual_value != null && m.target_value ? `${Math.round((m.actual_value / m.target_value) * 100)}%` : "-"}
                  </span></td>
                  <td><button className="btn btn-danger btn-sm" onClick={() => remove(m.id)}>Delete</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
