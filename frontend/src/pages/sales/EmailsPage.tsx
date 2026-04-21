import { useGetEmailsQuery, useIngestEmailMutation } from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";

export default function EmailsPage() {
  const { data: emails = [], refetch } = useGetEmailsQuery({});
  const [ingestEmail] = useIngestEmailMutation();

  return (
    <div>
      <PageHeader title="Emails" subtitle="Contact-linked email log (inbound and outbound)." />
      <CommandBar
        items={[
          {
            key: "log", label: "Log email", variant: "primary",
            onClick: async () => {
              const from = prompt("From email:"); if (!from) return;
              const to = prompt("To email:"); if (!to) return;
              const subject = prompt("Subject:") || "";
              const body = prompt("Body:") || "";
              await ingestEmail({ direction: "inbound", from_email: from, to_email: to, subject, body });
              refetch();
            },
          },
        ]}
      />
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>Direction</th><th>Subject</th><th>From</th><th>To</th><th>When</th></tr></thead>
          <tbody>
            {emails.map((e: any) => (
              <tr key={e.id}>
                <td><span className={`badge ${e.direction === "inbound" ? "badge-blue" : "badge-green"}`}>{e.direction}</span></td>
                <td style={{ fontWeight: 500 }}>{e.subject || "(no subject)"}</td>
                <td style={{ fontSize: "0.82rem" }}>{e.from_email}</td>
                <td style={{ fontSize: "0.82rem" }}>{e.to_email}</td>
                <td style={{ fontSize: "0.75rem" }}>{e.sent_at ? new Date(e.sent_at).toLocaleDateString() : ""}</td>
              </tr>
            ))}
            {emails.length === 0 && <tr><td colSpan={5} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No emails logged.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
