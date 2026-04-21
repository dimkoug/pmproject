import { useMemo, useState } from "react";
import { useGetAclPermissionsQuery } from "../../services/api";
import PageHeader from "../../shell/PageHeader";

export default function AclPermissionsPage() {
  const { data: permissions = [] } = useGetAclPermissionsQuery();
  const [filter, setFilter] = useState("");
  const [category, setCategory] = useState<string>("");

  const categories = useMemo(() => {
    const s = new Set<string>();
    permissions.forEach((p: any) => s.add(p.category));
    return Array.from(s).sort();
  }, [permissions]);

  const filtered = permissions.filter((p: any) => {
    if (category && p.category !== category) return false;
    if (!filter) return true;
    const q = filter.toLowerCase();
    return p.codename.toLowerCase().includes(q) || p.name.toLowerCase().includes(q) || (p.description || "").toLowerCase().includes(q);
  });

  return (
    <div>
      <PageHeader
        title="Permissions"
        subtitle="The full catalog of codenames the backend recognises. Read-only — the catalog is seeded from code on every startup."
        breadcrumbs={[{ to: "/admin", label: "Admin" }, { label: "Permissions" }]}
      />

      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem", flexWrap: "wrap" }}>
        <input
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter by codename / name / description…"
          style={{ flex: 1, minWidth: 240, padding: "0.5rem 0.75rem", border: "1px solid var(--gray-200)", borderRadius: "var(--radius)", fontSize: "0.85rem" }}
        />
        <select value={category} onChange={(e) => setCategory(e.target.value)} style={{ padding: "0.5rem 0.75rem", borderRadius: "var(--radius)" }}>
          <option value="">All categories</option>
          {categories.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <span className="badge badge-gray" style={{ alignSelf: "center" }}>{filtered.length} / {permissions.length}</span>
      </div>

      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead>
            <tr>
              <th>Codename</th>
              <th>Name</th>
              <th>Category</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((p: any) => (
              <tr key={p.id}>
                <td style={{ fontFamily: "monospace", fontSize: "0.78rem" }}>{p.codename}</td>
                <td style={{ fontWeight: 500 }}>{p.name}</td>
                <td><span className="badge badge-blue">{p.category}</span></td>
                <td style={{ color: "var(--gray-500)", fontSize: "0.82rem" }}>{p.description || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
