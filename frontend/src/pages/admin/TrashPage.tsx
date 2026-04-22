import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import PageHeader from "../../shell/PageHeader";
import DataTable from "../../shell/DataTable";
import { Icon } from "../../shell/icons";
import { useFormat } from "../../i18n/format";
import { confirmAction, notifyUser } from "../../shell/modalService";
import { useAppSelector } from "../../app/hooks";
import { useSavedFilter } from "../../shell/useSavedFilter";

const API = (import.meta.env.VITE_API_URL as string) || "";

type TrashRow = {
  entity: string;
  id: string;
  title: string;
  deleted_at: string | null;
};

export default function TrashPage() {
  const token = useAppSelector((s) => s.auth.token);
  const [rows, setRows] = useState<TrashRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [savedFilters, setSavedFilters] = useSavedFilter("admin-trash", { entity: "" });
  const filter = savedFilters.entity;
  const { formatDateTime } = useFormat();

  const load = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const qs = filter ? `?entity=${filter}` : "";
      const r = await fetch(`${API}/api/admin/trash${qs}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setRows(await r.json());
    } catch (e: any) {
      await notifyUser({ title: "Load failed", description: e?.message });
    } finally {
      setLoading(false);
    }
  };

  // Load on mount / filter change
  useMemo(() => { void load(); }, [filter]); // eslint-disable-line react-hooks/exhaustive-deps

  const restore = async (row: TrashRow) => {
    if (!token) return;
    const r = await fetch(`${API}/api/admin/trash/${row.entity}/${row.id}/restore`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!r.ok) {
      await notifyUser({ title: "Restore failed", description: `HTTP ${r.status}` });
      return;
    }
    await notifyUser({ title: "Restored", description: `${row.entity} · ${row.title}` });
    await load();
  };

  const purge = async (row: TrashRow) => {
    if (!token) return;
    const ok = await confirmAction({
      title: `Permanently delete ${row.title}?`,
      description: "This cannot be undone. The row + all its descendants will be removed from the database.",
      submitLabel: "Delete forever",
      dangerous: true,
    });
    if (!ok) return;
    const r = await fetch(`${API}/api/admin/trash/${row.entity}/${row.id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (r.status !== 204) {
      await notifyUser({ title: "Purge failed", description: `HTTP ${r.status}` });
      return;
    }
    await load();
  };

  const bulkRestore = async (selected: TrashRow[]) => {
    if (!token || selected.length === 0) return;
    let ok = 0; let failed = 0;
    for (const row of selected) {
      const r = await fetch(`${API}/api/admin/trash/${row.entity}/${row.id}/restore`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      r.ok ? ok++ : failed++;
    }
    await notifyUser({
      title: failed ? "Partial restore" : "Restored",
      description: `${ok} restored${failed ? `, ${failed} failed` : ""}.`,
    });
    await load();
  };

  const bulkPurge = async (selected: TrashRow[]) => {
    if (!token || selected.length === 0) return;
    const ok = await confirmAction({
      title: `Permanently delete ${selected.length} items?`,
      description: "This cannot be undone. All selected rows and their descendants will be removed from the database.",
      submitLabel: `Delete ${selected.length} items`,
      dangerous: true,
    });
    if (!ok) return;
    let done = 0; let failed = 0;
    for (const row of selected) {
      const r = await fetch(`${API}/api/admin/trash/${row.entity}/${row.id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      r.status === 204 ? done++ : failed++;
    }
    await notifyUser({
      title: failed ? "Partial purge" : "Purged",
      description: `${done} deleted${failed ? `, ${failed} failed` : ""}.`,
    });
    await load();
  };

  const columns = useMemo<ColumnDef<TrashRow, any>[]>(
    () => [
      { accessorKey: "entity", header: "Type", cell: (c) => <span className="badge badge-gray">{c.getValue() as string}</span> },
      { accessorKey: "title", header: "Item", cell: (c) => <span style={{ fontWeight: 500 }}>{c.getValue() as string}</span> },
      { accessorKey: "deleted_at", header: "Trashed", cell: (c) => formatDateTime(c.getValue() as string | undefined) },
      {
        id: "actions",
        header: "Actions",
        enableSorting: false,
        cell: (c) => (
          <div style={{ display: "inline-flex", gap: "0.25rem" }} onClick={(e) => e.stopPropagation()}>
            <button className="btn btn-sm" onClick={() => restore(c.row.original)}>
              <Icon.Refresh size={12} /> Restore
            </button>
            <button className="btn btn-sm btn-danger" onClick={() => purge(c.row.original)}>
              <Icon.Delete size={12} /> Purge
            </button>
          </div>
        ),
      },
    ],
    [formatDateTime],
  );

  return (
    <div>
      <PageHeader
        title="Trash"
        subtitle="Soft-deleted items across the workspace. Restore them here or purge permanently."
        breadcrumbs={[{ to: "/admin", label: "Admin" }, { label: "Trash" }]}
        meta={
          <div style={{ display: "inline-flex", gap: "0.4rem", alignItems: "center" }}>
            <label style={{ fontSize: "0.78rem", color: "var(--gray-500)" }}>Filter:</label>
            <select
              value={filter}
              onChange={(e) => setSavedFilters({ entity: e.target.value })}
              style={{ padding: "0.3rem 0.55rem", borderRadius: "var(--radius-sm)", border: "1px solid var(--gray-200)" }}
            >
              <option value="">All types</option>
              <option value="project">Projects</option>
              <option value="company">Companies</option>
              <option value="invoice">Invoices</option>
              <option value="document">Documents</option>
            </select>
          </div>
        }
      />
      <DataTable
        columns={columns}
        data={rows}
        isLoading={loading}
        enableSelection
        rowKey={(r) => `${r.entity}:${r.id}`}
        stateStorageKey="admin-trash"
        bulkActions={(selected, clear) => (
          <>
            <button className="btn btn-sm" onClick={() => bulkRestore(selected).then(clear)}>
              <Icon.Refresh size={12} /> Restore {selected.length}
            </button>
            <button className="btn btn-sm btn-danger" onClick={() => bulkPurge(selected).then(clear)}>
              <Icon.Delete size={12} /> Purge {selected.length}
            </button>
          </>
        )}
        emptyTitle="Trash is empty"
        emptyDescription="Nothing has been soft-deleted recently. Deleted items show up here for 30 days."
      />
    </div>
  );
}
