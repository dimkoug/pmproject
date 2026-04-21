import { useGetDmsPendingApprovalsQuery } from "../../services/api";
import PageHeader from "../../shell/PageHeader";

export default function PendingApprovalsPage() {
  const { data } = useGetDmsPendingApprovalsQuery();

  return (
    <div>
      <PageHeader
        title="Pending approvals"
        subtitle="Document workflows and signature requests waiting for action."
        breadcrumbs={[{ to: "/documents", label: "Documents" }, { label: "Reports" }, { label: "Pending approvals" }]}
      />
      {!data ? <div>Loading…</div> : (
        <>
          <div className="card">
            <div className="card-header">
              <h3>Workflows in progress</h3>
              <span className="badge badge-gray">{data.workflows?.length || 0}</span>
            </div>
            {data.workflows?.length === 0 ? (
              <div style={{ color: "var(--gray-500)", fontSize: "0.85rem" }}>None.</div>
            ) : (
              <table>
                <thead><tr><th>Workflow</th><th>Document</th><th>Current step</th><th>Started</th></tr></thead>
                <tbody>
                  {data.workflows?.map((w: any) => (
                    <tr key={w.id}>
                      <td style={{ fontWeight: 500 }}>{w.name}</td>
                      <td style={{ fontSize: "0.75rem", fontFamily: "monospace" }}>{w.document_id.slice(0, 8)}…</td>
                      <td>Step {w.current_step + 1}</td>
                      <td style={{ fontSize: "0.82rem" }}>{new Date(w.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="card" style={{ marginTop: "1rem" }}>
            <div className="card-header">
              <h3>Signatures awaiting</h3>
              <span className="badge badge-gray">{data.signatures?.length || 0}</span>
            </div>
            {data.signatures?.length === 0 ? (
              <div style={{ color: "var(--gray-500)", fontSize: "0.85rem" }}>None.</div>
            ) : (
              <table>
                <thead><tr><th>Signer</th><th>Document</th><th>Requested</th></tr></thead>
                <tbody>
                  {data.signatures?.map((s: any) => (
                    <tr key={s.id}>
                      <td>{s.signer_email}</td>
                      <td style={{ fontSize: "0.75rem", fontFamily: "monospace" }}>{s.document_id.slice(0, 8)}…</td>
                      <td style={{ fontSize: "0.82rem" }}>{new Date(s.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  );
}
