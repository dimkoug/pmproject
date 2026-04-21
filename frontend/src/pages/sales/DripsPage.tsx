import {
  useGetDripsQuery, useCreateDripMutation, useEnrollDripMutation, useDripTickMutation,
  useGetCrmContactsQuery,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";

export default function DripsPage() {
  const { data: drips = [], refetch } = useGetDripsQuery();
  const { data: contacts = [] } = useGetCrmContactsQuery(undefined);
  const [createDrip] = useCreateDripMutation();
  const [enrollDrip] = useEnrollDripMutation();
  const [dripTick] = useDripTickMutation();

  return (
    <div>
      <PageHeader title="Drip sequences" subtitle="Automated scheduled email sequences enrolling contacts over time." />
      <CommandBar
        items={[
          {
            key: "tick", label: "Run tick",
            onClick: async () => {
              const r: any = await dripTick();
              alert(`Advanced ${r.data?.advanced || 0}, sent ${r.data?.emails_sent || 0}`);
            },
          },
          {
            key: "new", label: "New sequence", variant: "primary",
            onClick: async () => {
              const name = prompt("Sequence name:"); if (!name) return;
              const subj = prompt("Step 1 subject:"); if (!subj) return;
              const body = prompt("Step 1 body:") || "";
              await createDrip({ name, steps: [{ step_order: 0, delay_days: 0, subject: subj, body }] });
              refetch();
            },
          },
        ]}
      />
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>Name</th><th>Steps</th><th>Active</th><th>Actions</th></tr></thead>
          <tbody>
            {drips.map((d: any) => (
              <tr key={d.id}>
                <td style={{ fontWeight: 500 }}>{d.name}</td>
                <td>{d.step_count}</td>
                <td>{d.is_active ? "Yes" : "No"}</td>
                <td>
                  <button className="btn btn-sm" onClick={async () => {
                    if (!contacts.length) { alert("No contacts"); return; }
                    const cid = prompt("Contact ID:", contacts[0].id) || contacts[0].id;
                    await enrollDrip({ sequence_id: d.id, contact_id: cid });
                    alert("Enrolled.");
                  }}>Enroll contact</button>
                </td>
              </tr>
            ))}
            {drips.length === 0 && <tr><td colSpan={4} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No sequences.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
