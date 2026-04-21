import {
  useGetRetentionPoliciesQuery, useCreateRetentionPolicyMutation, useApplyRetentionMutation,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";

export default function RetentionPage() {
  const { data: policies = [], refetch } = useGetRetentionPoliciesQuery();
  const [createPolicy] = useCreateRetentionPolicyMutation();
  const [applyRetention] = useApplyRetentionMutation();

  return (
    <div>
      <PageHeader title="Retention policies" subtitle="Archive or delete documents after a configurable age." />
      <CommandBar
        items={[
          {
            key: "apply", label: "Apply now",
            onClick: async () => {
              const r: any = await applyRetention();
              alert(`Archived ${r.data?.archived || 0}, deleted ${r.data?.deleted || 0}`);
              refetch();
            },
          },
          {
            key: "new", label: "New policy", variant: "primary",
            onClick: async () => {
              const name = prompt("Policy name:"); if (!name) return;
              const days = parseInt(prompt("Days after last update:") || "0"); if (!days) return;
              const action = prompt("Action (archive/delete):", "archive") || "archive";
              await createPolicy({ name, days_after: days, action }); refetch();
            },
          },
        ]}
      />
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>Name</th><th>Folder / Tag</th><th>Days</th><th>Action</th><th>Active</th></tr></thead>
          <tbody>
            {policies.map((p: any) => (
              <tr key={p.id}>
                <td style={{ fontWeight: 500 }}>{p.name}</td>
                <td style={{ fontSize: "0.82rem" }}>{p.tag_match ? `tag: ${p.tag_match}` : p.folder_id ? "folder" : "all"}</td>
                <td>{p.days_after}</td>
                <td><span className="badge badge-blue">{p.action}</span></td>
                <td>{p.is_active ? <span className="badge badge-green">Yes</span> : <span className="badge badge-gray">No</span>}</td>
              </tr>
            ))}
            {policies.length === 0 && <tr><td colSpan={5} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No policies.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
