import { useState } from "react";
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
    const codename = prompt("Codename (e.g. finance.invoice.post):");
    if (!codename) return;
    const deny = confirm("OK = deny (revoke even if granted elsewhere). Cancel = allow.");
    const reason = prompt("Reason (optional):") ?? undefined;
    await upsertPerm({ userId: selected, codename, is_deny: deny, reason });
    rDirect();
  };

  const currentUser = users.find((u: any) => u.id === selected);

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
          {users.map((u: any) => (
            <button
              key={u.id}
              type="button"
              onClick={() => setSelected(u.id)}
              className={`app-nav-item ${selected === u.id ? "active" : ""}`}
              style={{ display: "block", width: "100%", textAlign: "left", border: 0, background: "transparent", cursor: "pointer", padding: "0.55rem 1rem" }}
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
                  <table>
                    <thead><tr><th>Codename</th><th>Type</th><th>Reason</th><th></th></tr></thead>
                    <tbody>
                      {directPerms.map((p: any) => (
                        <tr key={p.codename}>
                          <td style={{ fontFamily: "monospace", fontSize: "0.78rem" }}>{p.codename}</td>
                          <td>
                            {p.is_deny
                              ? <span className="badge badge-red">DENY</span>
                              : <span className="badge badge-green">ALLOW</span>}
                          </td>
                          <td style={{ fontSize: "0.82rem", color: "var(--gray-500)" }}>{p.reason || "—"}</td>
                          <td>
                            <button
                              className="btn btn-sm btn-danger"
                              onClick={async () => {
                                await deletePerm({ userId: selected!, codename: p.codename });
                                rDirect();
                              }}
                            >Remove</button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
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
