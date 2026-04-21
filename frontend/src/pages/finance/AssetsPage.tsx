import { useGetAssetsQuery, useCreateAssetMutation } from "../../services/api";
import { useProjectContext } from "../../shell/useProjectContext";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";

export default function AssetsPage() {
  const projectId = useProjectContext();
  const { data: assets = [], refetch } = useGetAssetsQuery(projectId);
  const [createAsset] = useCreateAssetMutation();

  return (
    <div>
      <PageHeader title="Assets" subtitle="Physical and intangible assets with value tracking." />
      <CommandBar
        items={[
          {
            key: "new", label: "New asset", variant: "primary",
            onClick: async () => {
              const name = prompt("Asset name:"); if (!name) return;
              await createAsset({ name, project_id: projectId });
              refetch();
            },
          },
        ]}
      />
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>Name</th><th>Tag</th><th>Category</th><th>Status</th><th>Value</th><th>Location</th></tr></thead>
          <tbody>
            {assets.map((a: any) => (
              <tr key={a.id}>
                <td style={{ fontWeight: 500 }}>{a.name}</td>
                <td>{a.asset_tag || "-"}</td>
                <td>{a.category || "-"}</td>
                <td><span className="badge badge-blue">{a.status}</span></td>
                <td>${a.current_value?.toLocaleString() || "-"}</td>
                <td>{a.location || "-"}</td>
              </tr>
            ))}
            {assets.length === 0 && <tr><td colSpan={6} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No assets.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
