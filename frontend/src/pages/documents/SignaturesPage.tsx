import { useGetSignaturesQuery, useCreateSignatureMutation } from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";

export default function SignaturesPage() {
  const { data: sigs = [], refetch } = useGetSignaturesQuery();
  const [createSig] = useCreateSignatureMutation();

  return (
    <div>
      <PageHeader title="E-Signature requests" subtitle="Send documents for signature and track completion." />
      <CommandBar
        items={[
          {
            key: "request", label: "Request signature", variant: "primary",
            onClick: async () => {
              const docId = prompt("Document ID:");
              const email = prompt("Signer email:");
              if (docId && email) { await createSig({ document_id: docId, signer_email: email }); refetch(); }
            },
          },
        ]}
      />
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>Signer</th><th>Document</th><th>Status</th><th>Signed</th><th>Link</th></tr></thead>
          <tbody>
            {sigs.map((s: any) => (
              <tr key={s.id}>
                <td>{s.signer_email}</td>
                <td style={{ fontSize: "0.75rem" }}>{s.document_id.slice(0, 8)}…</td>
                <td><span className={`badge ${s.status === "signed" ? "badge-green" : s.status === "declined" ? "badge-red" : "badge-yellow"}`}>{s.status}</span></td>
                <td>{s.signed_at ? new Date(s.signed_at).toLocaleDateString() : "-"}</td>
                <td style={{ fontSize: "0.72rem", fontFamily: "monospace" }}>{s.token?.slice(0, 16)}…</td>
              </tr>
            ))}
            {sigs.length === 0 && <tr><td colSpan={5} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No signature requests.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
