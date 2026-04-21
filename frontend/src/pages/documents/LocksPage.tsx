import { useGetLocksQuery, useCheckinDocMutation } from "../../services/api";
import PageHeader from "../../shell/PageHeader";

export default function LocksPage() {
  const { data: locks = [], refetch } = useGetLocksQuery();
  const [checkinDoc] = useCheckinDocMutation();

  return (
    <div>
      <PageHeader title="Checked-out documents" subtitle="Documents currently locked by a user. Force check-in releases the lock." />
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>Document</th><th>User</th><th>Locked at</th><th>Note</th><th>Actions</th></tr></thead>
          <tbody>
            {locks.map((l: any) => (
              <tr key={l.document_id}>
                <td style={{ fontWeight: 500 }}>{l.title || l.document_id.slice(0, 8) + "…"}</td>
                <td style={{ fontSize: "0.75rem" }}>{l.user_id.slice(0, 8)}…</td>
                <td style={{ fontSize: "0.82rem" }}>{l.locked_at ? new Date(l.locked_at).toLocaleString() : ""}</td>
                <td style={{ fontSize: "0.82rem" }}>{l.note || "-"}</td>
                <td>
                  <button className="btn btn-sm" onClick={async () => { await checkinDoc(l.document_id); refetch(); }}>
                    Force check-in
                  </button>
                </td>
              </tr>
            ))}
            {locks.length === 0 && <tr><td colSpan={5} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No active locks.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
