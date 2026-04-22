import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import {
  useGetAdminUsersQuery,
  useGetAclGroupsQuery,
  useGetUserAclGroupsQuery,
  useSetUserAclGroupsMutation,
  useGetAclPermissionsQuery,
  useGetUserDirectPermissionsQuery,
  useUpsertUserPermissionMutation,
  useDeleteUserPermissionMutation,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";
import { promptForValues } from "../../shell/modalService";

type AdminUser = {
  id: string;
  name?: string;
  email: string;
  role: string;
};

type DirectPerm = {
  codename: string;
  is_deny: boolean;
  reason?: string;
};

export default function AclUsersPage() {
  const { data: users = [] } = useGetAdminUsersQuery();
  const { data: groups = [] } = useGetAclGroupsQuery();
  const { data: permissions = [] } = useGetAclPermissionsQuery();
  const [selected, setSelected] = useState<string | null>(null);
  const { data: userGroups = [], refetch: rUserGroups } = useGetUserAclGroupsQuery(selected!, { skip: !selected });
  const { data: directPerms = [], refetch: rDirect } = useGetUserDirectPermissionsQuery(selected!, { skip: !selected });
  const [setUserGroups] = useSetUserAclGroupsMutation();
  const [upsertPerm] = useUpsertUserPermissionMutation();
  const [deletePerm] = useDeleteUserPermissionMutation();
  const { open: openPeek } = useDrawerPeek();

  const toggleGroup = async (groupId: string) => {
    if (!selected) return;
    const ids = new Set(userGroups.map((g: any) => g.id));
    if (ids.has(groupId)) ids.delete(groupId);
    else ids.add(groupId);
    await setUserGroups({ userId: selected, group_ids: Array.from(ids) });
    rUserGroups();
  };

  const addDirectPerm = async () => {
    if (!selected) return;
    const v = await promptForValues({
      title: "Add direct permission",
      submitLabel: "Add",
      fields: [
        { name: "codename", label: "Codename", placeholder: "e.g. finance.invoice.post", required: true },
        {
          name: "mode", label: "Type", kind: "select", required: true, defaultValue: "allow",
          options: [
            { value: "allow", label: "Allow" },
            { value: "deny", label: "Deny (revoke even if granted elsewhere)" },
          ],
        },
        { name: "reason", label: "Reason", placeholder: "Optional" },
      ],
    });
    if (!v) return;
    await upsertPerm({
      userId: selected,
      codename: v.codename,
      is_deny: v.mode === "deny",
      reason: v.reason || undefined,
    });
    rDirect();
  };

  const currentUser = users.find((u: any) => u.id === selected);

  const directPermColumns = useMemo<ColumnDef<DirectPerm, any>[]>(
    () => [
      {
        accessorKey: "codename",
        header: "Codename",
        cell: (c) => <span style={{ fontFamily: "monospace", fontSize: "0.78rem" }}>{c.getValue() as string}</span>,
      },
      {
        accessorKey: "is_deny",
        header: "Type",
        cell: (c) =>
          c.getValue() ? (
            <span className="badge badge-red">DENY</span>
          ) : (
            <span className="badge badge-green">ALLOW</span>
          ),
      },
      {
        accessorKey: "reason",
        header: "Reason",
        cell: (c) => <span style={{ fontSize: "0.82rem", color: "var(--gray-500)" }}>{(c.getValue() as string) || "—"}</span>,
      },
      {
        id: "actions",
        header: "",
        enableSorting: false,
        cell: (c) => (
          <button
            className="btn btn-sm btn-danger"
            onClick={async (e) => {
              e.stopPropagation();
              await deletePerm({ userId: selected!, codename: c.row.original.codename });
              rDirect();
            }}
          >
            Remove
          </button>
        ),
      },
    ],
    [deletePerm, rDirect, selected],
  );

  return (
    <div>
      <PageHeader
        title="Users"
        subtitle="Assign groups and override individual permissions. Deny overrides always win."
        breadcrumbs={[{ to: "/admin", label: "Admin" }, { label: "Users" }]}
      />

      <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: "1rem" }}>
        <div className="card" style={{ padding: 0 }}>
          <div style={{ padding: "0.75rem 1rem", fontSize: "0.78rem", fontWeight: 600, color: "var(--gray-500)", borderBottom: "1px solid var(--gray-200)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
            {users.length} users
          </div>
          {(users as AdminUser[]).map((u) => (
            <button
              key={u.id}
              type="button"
              onClick={() => setSelected(u.id)}
              onDoubleClick={() => openPeek("user", u.id)}
              className={`app-nav-item ${selected === u.id ? "active" : ""}`}
              style={{ display: "block", width: "100%", textAlign: "left", border: 0, background: "transparent", cursor: "pointer", padding: "0.55rem 1rem" }}
              title="Click to edit, double-click for detail peek"
            >
              <div style={{ fontWeight: 600 }}>{u.name || u.email}</div>
              <div style={{ fontSize: "0.72rem", color: "var(--gray-500)" }}>
                {u.email} · <span className="badge badge-blue" style={{ fontSize: "0.6rem" }}>{u.role}</span>
              </div>
            </button>
          ))}
        </div>

        <div>
          {!currentUser ? (
            <div className="card" style={{ textAlign: "center", padding: "3rem 2rem", color: "var(--gray-500)" }}>
              Select a user.
            </div>
          ) : (
            <>
              <div className="card">
                <div className="card-header">
                  <h3>{currentUser.name} — groups</h3>
                  <span className="badge badge-gray">{userGroups.length}</span>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: "0.3rem" }}>
                  {groups.map((g: any) => {
                    const member = userGroups.some((ug: any) => ug.id === g.id);
                    return (
                      <label key={g.id} style={{ display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.4rem 0.5rem", cursor: "pointer", fontSize: "0.85rem" }}>
                        <input type="checkbox" checked={member} onChange={() => toggleGroup(g.id)} />
                        <span>{g.name}</span>
                        {g.is_system && <span className="badge badge-gray" style={{ fontSize: "0.6rem" }}>system</span>}
                      </label>
                    );
                  })}
                </div>
              </div>

              <div className="card">
                <div className="card-header">
                  <h3>Direct permissions &amp; denies</h3>
                  <button className="btn btn-sm btn-primary" onClick={addDirectPerm}>+ Add</button>
                </div>
                {directPerms.length === 0 ? (
                  <div style={{ color: "var(--gray-500)", fontSize: "0.85rem" }}>
                    None. User inherits permissions only via their groups{currentUser.role === "admin" ? " and the admin role" : ""}.
                  </div>
                ) : (
                  <DataTable
                    columns={directPermColumns}
                    data={directPerms as DirectPerm[]}
                    emptyTitle="No direct permissions"
                    emptyDescription="User inherits via their groups only."
                    rowKey={(row) => row.codename}
                    globalSearch={false}
                    defaultPageSize={100}
                  />
                )}
              </div>
              <div style={{ fontSize: "0.72rem", color: "var(--gray-500)" }}>
                {permissions.length} total permissions in the catalog.
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
