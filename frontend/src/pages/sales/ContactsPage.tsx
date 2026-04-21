import { useGetCrmContactsQuery, useCreateCrmContactMutation } from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";

export default function ContactsPage() {
  const { data: contacts = [], refetch } = useGetCrmContactsQuery(undefined);
  const [createContact] = useCreateCrmContactMutation();

  return (
    <div>
      <PageHeader title="Contacts" subtitle="People at customer and prospect companies." />
      <CommandBar
        items={[
          {
            key: "new", label: "New contact", variant: "primary",
            onClick: async () => {
              const first_name = prompt("First name:"); if (!first_name) return;
              const last_name = prompt("Last name:") || "";
              const email = prompt("Email:") || "";
              await createContact({ first_name, last_name, email });
              refetch();
            },
          },
        ]}
      />
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>Name</th><th>Email</th><th>Phone</th><th>Title</th></tr></thead>
          <tbody>
            {contacts.map((c: any) => (
              <tr key={c.id}>
                <td style={{ fontWeight: 500 }}>{c.first_name} {c.last_name || ""}</td>
                <td>{c.email || "-"}</td>
                <td>{c.phone || "-"}</td>
                <td>{c.job_title || "-"}</td>
              </tr>
            ))}
            {contacts.length === 0 && <tr><td colSpan={4} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No contacts yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
