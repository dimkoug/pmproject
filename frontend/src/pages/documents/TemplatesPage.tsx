import {
  useGetDmsTemplatesQuery, useCreateDmsTemplateMutation, useInstantiateTemplateMutation,
} from "../../services/api";
import { useProjectContext } from "../../shell/useProjectContext";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";

export default function TemplatesPage() {
  const projectId = useProjectContext();
  const { data: templates = [], refetch } = useGetDmsTemplatesQuery();
  const [createTpl] = useCreateDmsTemplateMutation();
  const [instantiateTpl] = useInstantiateTemplateMutation();

  return (
    <div>
      <PageHeader title="Document templates" subtitle="Reusable document bodies with {{variable}} placeholders." />
      <CommandBar
        items={[
          {
            key: "new", label: "New template", variant: "primary",
            onClick: async () => {
              const name = prompt("Template name:"); if (!name) return;
              const body = prompt("Body (use {{var}} placeholders):"); if (!body) return;
              await createTpl({ name, body }); refetch();
            },
          },
        ]}
      />
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>Name</th><th>Category</th><th>Description</th><th>Actions</th></tr></thead>
          <tbody>
            {templates.map((t: any) => (
              <tr key={t.id}>
                <td style={{ fontWeight: 500 }}>{t.name}</td>
                <td>{t.category || "-"}</td>
                <td style={{ fontSize: "0.82rem", color: "var(--gray-500)" }}>{t.description || "-"}</td>
                <td>
                  <button className="btn btn-sm" onClick={async () => {
                    const title = prompt("New document title:"); if (!title) return;
                    await instantiateTpl({ templateId: t.id, body: { title, project_id: projectId, vars: {} } });
                  }}>Instantiate</button>
                </td>
              </tr>
            ))}
            {templates.length === 0 && <tr><td colSpan={4} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No templates.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
