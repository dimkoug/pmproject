import {
  useGetWorkflowsQuery, useCreateWorkflowMutation, useAdvanceWorkflowMutation,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import { promptForValues } from "../../shell/modalService";

export default function WorkflowsPage() {
  const { data: workflows = [], refetch } = useGetWorkflowsQuery();
  const [createWorkflow] = useCreateWorkflowMutation();
  const [advanceWorkflow] = useAdvanceWorkflowMutation();

  return (
    <div>
      <PageHeader title="Document workflows" subtitle="Multi-step approval flows (author → reviewer → approver)." />
      <CommandBar
        items={[
          {
            key: "new", label: "New workflow", variant: "primary",
            onClick: async () => {
              const v = await promptForValues({
                title: "New workflow",
                submitLabel: "Create",
                fields: [
                  { name: "docId", label: "Document ID", required: true },
                  { name: "name", label: "Workflow name", defaultValue: "Review" },
                ],
              });
              if (!v) return;
              await createWorkflow({
                document_id: v.docId, name: v.name || "Review", steps: [
                  { step_order: 0, role: "author" },
                  { step_order: 1, role: "reviewer" },
                  { step_order: 2, role: "approver" },
                ],
              });
              refetch();
            },
          },
        ]}
      />
      <div className="card" style={{ padding: 0 }}>
        {workflows.length === 0 && <div style={{ textAlign: "center", color: "var(--gray-500)", padding: "2rem" }}>No workflows.</div>}
        {workflows.map((w: any) => (
          <div key={w.id} style={{ padding: "0.75rem 1rem", borderTop: "1px solid var(--gray-100)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div><b>{w.name}</b> <span style={{ fontSize: "0.75rem", color: "var(--gray-500)", marginLeft: "0.5rem" }}>{w.document_id.slice(0, 8)}…</span></div>
              <span className={`badge ${w.is_complete ? "badge-green" : "badge-yellow"}`}>
                {w.is_complete ? "Complete" : `Step ${w.current_step + 1}`}
              </span>
            </div>
            <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem", flexWrap: "wrap" }}>
              {w.steps.map((s: any, i: number) => (
                <div key={s.id} style={{ padding: "0.3rem 0.6rem", border: `1px solid var(--gray-${s.status === "pending" ? "300" : "200"})`, borderRadius: 4, fontSize: "0.78rem", background: s.status === "approved" ? "#d1fae5" : s.status === "rejected" ? "#fee2e2" : i === w.current_step ? "#fef3c7" : "transparent" }}>
                  {s.role}{s.status !== "pending" && ` (${s.status})`}
                </div>
              ))}
            </div>
            {!w.is_complete && (
              <div style={{ display: "flex", gap: "0.25rem", marginTop: "0.5rem" }}>
                <button className="btn btn-sm btn-primary" onClick={async () => { await advanceWorkflow({ id: w.id, body: { decision: "approved" } }); refetch(); }}>
                  Approve step
                </button>
                <button className="btn btn-sm" onClick={async () => {
                  const v = await promptForValues({
                    title: "Reject step",
                    submitLabel: "Reject",
                    fields: [
                      { name: "note", label: "Reason", kind: "textarea", placeholder: "Optional" },
                    ],
                  });
                  if (!v) return;
                  await advanceWorkflow({ id: w.id, body: { decision: "rejected", note: v.note || "" } });
                  refetch();
                }}>Reject</button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
