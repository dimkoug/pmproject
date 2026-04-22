import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { useGetAclPermissionsQuery } from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import DataTable from "../../shell/DataTable";

type Permission = {
  id: string;
  codename: string;
  name: string;
  category: string;
  description?: string;
};

export default function AclPermissionsPage() {
  const { data: permissions = [], isLoading } = useGetAclPermissionsQuery();
  const [category, setCategory] = useState<string>("");

  const categories = useMemo(() => {
    const s = new Set<string>();
    permissions.forEach((p: any) => s.add(p.category));
    return Array.from(s).sort();
  }, [permissions]);

  const filtered = useMemo<Permission[]>(
    () => (category ? permissions.filter((p: any) => p.category === category) : permissions) as Permission[],
    [category, permissions],
  );

  const columns = useMemo<ColumnDef<Permission, any>[]>(
    () => [
      {
        accessorKey: "codename",
        header: "Codename",
        cell: (c) => <span style={{ fontFamily: "monospace", fontSize: "0.78rem" }}>{c.getValue() as string}</span>,
      },
      { accessorKey: "name", header: "Name", cell: (c) => <span style={{ fontWeight: 500 }}>{c.getValue() as string}</span> },
      {
        accessorKey: "category",
        header: "Category",
        cell: (c) => <span className="badge badge-blue">{c.getValue() as string}</span>,
      },
      {
        accessorKey: "description",
        header: "Description",
        cell: (c) => <span style={{ color: "var(--gray-500)", fontSize: "0.82rem" }}>{(c.getValue() as string) || "—"}</span>,
      },
    ],
    [],
  );

  return (
    <div>
      <PageHeader
        title="Permissions"
        subtitle="The full catalog of codenames the backend recognises. Read-only — the catalog is seeded from code on every startup."
        breadcrumbs={[{ to: "/admin", label: "Admin" }, { label: "Permissions" }]}
      />

      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem", flexWrap: "wrap", alignItems: "center" }}>
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          style={{ padding: "0.4rem 0.65rem", borderRadius: "var(--radius-sm)", border: "1px solid var(--gray-200)" }}
        >
          <option value="">All categories</option>
          {categories.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <span className="badge badge-gray">{filtered.length} / {permissions.length}</span>
      </div>

      <DataTable
        columns={columns}
        data={filtered}
        isLoading={isLoading}
        searchPlaceholder="Filter codename / name / description…"
        emptyTitle="No permissions match"
        emptyDescription="Try clearing the category filter."
      />
    </div>
  );
}
