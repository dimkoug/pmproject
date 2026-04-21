import { useGetFollowUpsDueQuery, useCompleteFollowUpMutation } from "../../services/api";
import PageHeader from "../../shell/PageHeader";

export default function FollowUpsPage() {
  const { data: followUps = [], refetch } = useGetFollowUpsDueQuery();
  const [completeFollowUp] = useCompleteFollowUpMutation();

  return (
    <div>
      <PageHeader title="Follow-ups" subtitle="Due today and overdue interactions across all contacts." />
      <div className="card" style={{ padding: 0 }}>
        {followUps.length === 0 ? (
          <div style={{ padding: "2rem", textAlign: "center", color: "var(--gray-500)" }}>Nothing due.</div>
        ) : (
          <table>
            <thead><tr><th>Subject</th><th>Due</th><th>Contact</th><th>Actions</th></tr></thead>
            <tbody>
              {followUps.map((f: any) => (
                <tr key={f.id}>
                  <td style={{ fontWeight: 500 }}>{f.subject}</td>
                  <td>{f.follow_up_date}</td>
                  <td style={{ fontSize: "0.75rem" }}>{f.contact_id ? `${f.contact_id.slice(0, 8)}…` : "-"}</td>
                  <td>
                    <button className="btn btn-sm" onClick={async () => { await completeFollowUp(f.id); refetch(); }}>Done</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
