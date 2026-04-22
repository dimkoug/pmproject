import { useState } from "react";
import {
  useGetAclGroupsQuery,
  useCreateAclGroupMutation,
  useDeleteAclGroupMutation,
  useGetAclPermissionsQuery,
  useGetGroupPermissionsQuery,
  useSetGroupPermissionsMutation,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import { promptForValues, confirmAction } from "../../shell/modalService";

export default function AclGroupsPage() {
  const { data: groups = [], refetch: rGroups } = useGetAclGroupsQuery();
  const { data: permissions = [] } = useGetAclPermissionsQuery();
  const [createGroup] = useCreateAclGroupMutation();
  const [deleteGroup] = useDeleteAclGroupMutation();
  const [setGroupPerms] = useSetGroupPermissionsMutation();
  const [selected, setSelected] = useState<string | null>(null);
  const { data: groupPerms = [], refetch: rGroupPerms } = useGetGroupPermissionsQuery(selected!, { skip: !selected });
  const [editPerms, setEditPerms] = useState<Set<string> | null>(null);

  const current = groups.find((g: any) => g.id === selected);
  const working = editPerms ?? new Set(groupPerms);
  const isDirty = editPerms !== null;

  const togglePerm = (code: string) => {
    const next = new Set(working);
    if (next.has(code)) next.delete(code);
    else next.add(code);
    setEditPerms(next);
  };

  const save = async () => {
    if (!selected || !editPerms) return;
    await setGroupPerms({ groupId: selected, codenames: Array.from(editPerms) });
    setEditPerms(null);
    rGroupPerms();
  };

  const byCategory = permissions.reduce((acc: Record<string, any[]>, p: any) => {
    (acc[p.category] ||= []).push(p);
    return acc;
  }, {});

  return (
    <div>
      <PageHeader
        title="Groups"
        subtitle="ACL groups bundle permissions. Assign users to groups to grant them bundled access."
        breadcrumbs={[{ to: "/admin", label: "Admin" }, { label: "Groups" }]}
      />
      <CommandBar
        items={[
          {
            key: "new",
            label: "+ New group",
            variant: "primary",
            onClick: async () => {
              const v = await promptForValues({
                title: "New group",
                submitLabel: "Create",
                fields: [
                  { name: "name", label: "Group name", required: true },
                  { name: "description", label: "Description", placeholder: "Optional" },
                ],
              });
              if (!v) return;
              await createGroup({ name: v.name, description: v.description || undefined });
              rGroups();
            },
          },
          {
            key: "delete",
            label: "Delete",
            variant: "danger",
            disabled: !current || current.is_system,
            title: current?.is_system ? "System groups cannot be deleted" : undefined,
            onClick: async () => {
              if (!current) return;
              const ok = await confirmAction({
                title: "Delete group?",
                description: `Delete group "${current.name}"?`,
                submitLabel: "Delete",
                dangerous: true,
              });
              if (!ok) return;
              await deleteGroup(current.id);
              setSelected(null);
              rGroups();
            },
          },
          {
            key: "save",
            label: "Save permissions",
            variant: "primary",
            disabled: !selected || !isDirty,
            onClick: save,
          },
          {
            key: "revert",
            label: "Revert",
            disabled: !isDirty,
            onClick: () => setEditPerms(null),
          },
        ]}
      />

      <div style={{ display: "grid", gridTemplateColumns: "280px 1fr", gap: "1rem" }}>
        <div className="card" style={{ padding: 0 }}>
          <div style={{ padding: "0.75rem 1rem", fontSize: "0.78rem", fontWeight: 600, color: "var(--gray-500)", borderBottom: "1px solid var(--gray-200)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
            {groups.length} groups
          </div>
          {groups.map((g: any) => (
            <button
              key={g.id}
              type="button"
              onClick={() => { setSelected(g.id); setEditPerms(null); }}
              className={`app-nav-item ${selected === g.id ? "active" : ""}`}
              style={{ display: "block", width: "100%", textAlign: "left", border: 0, background: "transparent", cursor: "pointer", padding: "0.55rem 1rem" }}
            >
              <div style={{ fontWeight: 600 }}>{g.name}</div>
              <div style={{ fontSize: "0.72rem", color: "var(--gray-500)" }}>
                {g.is_system ? "System" : "Custom"}{g.description ? ` · ${g.description.slice(0, 40)}` : ""}
              </div>
            </button>
          ))}
        </div>

        <div>
          {current ? (
            <div className="card">
              <div className="card-header">
                <h3>{current.name} — permissions</h3>
                <span className="badge badge-gray">{working.size} / {permissions.length}</span>
              </div>
              {Object.entries(byCategory).sort().map(([category, perms]) => (
                <div key={category} style={{ marginBottom: "1rem" }}>
                  <div style={{ fontSize: "0.7rem", fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--gray-500)", marginBottom: "0.4rem" }}>
                    {category}
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: "0.3rem" }}>
                    {(perms as any[]).map((p) => (
                      <label key={p.id} style={{ display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.4rem 0.5rem", cursor: "pointer", borderRadius: 6, fontSize: "0.82rem" }}>
                        <input
                          type="checkbox"
                          checked={working.has(p.codename)}
                          onChange={() => togglePerm(p.codename)}
                        />
                        <span style={{ fontFamily: "monospace", fontSize: "0.75rem" }}>{p.codename}</span>
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="card" style={{ textAlign: "center", padding: "3rem 2rem", color: "var(--gray-500)" }}>
              Select a group to edit its permissions.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
