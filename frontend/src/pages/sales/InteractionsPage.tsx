import { useGetInteractionsQuery, useCreateInteractionMutation } from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";

const INTERACTION_TYPES = ["call", "email", "meeting", "note", "demo"];

export default function InteractionsPage() {
  const { data: interactions = [], refetch } = useGetInteractionsQuery({});
  const [createInteraction] = useCreateInteractionMutation();

  return (
    <div>
      <PageHeader title="Interactions" subtitle="Logged calls, emails, meetings, demos, and notes." />
      <CommandBar
        items={[
          {
            key: "new", label: "Log interaction", variant: "primary",
            onClick: async () => {
              const subject = prompt("Subject:"); if (!subject) return;
              const interaction_type = prompt(`Type (${INTERACTION_TYPES.join("/")}):`, "note") || "note";
              const body = prompt("Notes (optional):") || "";
              await createInteraction({ subject, interaction_type, body });
              refetch();
            },
          },
        ]}
      />
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>Type</th><th>Subject</th><th>Date</th><th>Notes</th></tr></thead>
          <tbody>
            {interactions.map((i: any) => (
              <tr key={i.id}>
                <td><span className="badge badge-blue">{i.interaction_type}</span></td>
                <td style={{ fontWeight: 500 }}>{i.subject}</td>
                <td>{i.interaction_date || "-"}</td>
                <td style={{ fontSize: "0.82rem", color: "var(--gray-500)" }}>{i.body?.slice(0, 80) || "-"}</td>
              </tr>
            ))}
            {interactions.length === 0 && <tr><td colSpan={4} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No interactions logged.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
