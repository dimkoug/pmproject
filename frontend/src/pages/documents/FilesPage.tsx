import { useState } from "react";
import {
  useGetFoldersQuery, useCreateFolderMutation,
  useGetDocumentsQuery, useGetDocVersionsQuery, useSearchDocumentsQuery,
  useCheckoutDocMutation, useCheckinDocMutation,
  useGetExpiringDocumentsQuery, useRestoreDocVersionMutation,
  useGetDocShareLinksQuery, useCreateDocShareLinkMutation, useRevokeDocShareLinkMutation,
  useGetFolderPermissionsQuery, useGrantFolderPermissionMutation, useRevokeFolderPermissionMutation,
  useGetAdminUsersQuery,
} from "../../services/api";
import { useProjectContext } from "../../shell/useProjectContext";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function FilesPage() {
  const projectId = useProjectContext();
  const [currentFolder, setCurrentFolder] = useState<string | undefined>(undefined);
  const [folderPath, setFolderPath] = useState<{ id: string; name: string }[]>([]);
  const { data: folders = [], refetch: rFolders } = useGetFoldersQuery({ projectId, parentId: currentFolder });
  const { data: docs = [], refetch: rDocs } = useGetDocumentsQuery({ folderId: currentFolder, projectId });
  const { data: expiring = [] } = useGetExpiringDocumentsQuery(30);
  const [createFolder] = useCreateFolderMutation();

  // Search + filters
  const [searchQ, setSearchQ] = useState("");
  const [fullText, setFullText] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [fDateFrom, setFDateFrom] = useState("");
  const [fDateTo, setFDateTo] = useState("");
  const [fStatus, setFStatus] = useState("");
  const [fAuthor, setFAuthor] = useState("");
  const [fType, setFType] = useState("");
  const { data: searchResults = [] } = useSearchDocumentsQuery(
    { q: searchQ, fullText, dateFrom: fDateFrom || undefined, dateTo: fDateTo || undefined,
      status: fStatus || undefined, authorId: fAuthor || undefined, fileType: fType || undefined },
    { skip: searchQ.length < 2 }
  );

  const [checkoutDoc] = useCheckoutDocMutation();
  const [checkinDoc] = useCheckinDocMutation();
  const [restoreVersion] = useRestoreDocVersionMutation();

  const [showNewFolder, setShowNewFolder] = useState(false);
  const [folderName, setFolderName] = useState("");

  // Upload state — supports optional expiry
  const [pendingUpload, setPendingUpload] = useState<File | null>(null);
  const [uploadExpiry, setUploadExpiry] = useState("");

  const [versionDocId, setVersionDocId] = useState<string | null>(null);
  const { data: versions = [], refetch: rVersions } = useGetDocVersionsQuery(versionDocId!, { skip: !versionDocId });

  // Share dialog
  const [shareDocId, setShareDocId] = useState<string | null>(null);

  // Permissions editor
  const [permFolder, setPermFolder] = useState<{ id: string; name: string } | null>(null);

  const navigateToFolder = (id: string, name: string) => {
    setFolderPath([...folderPath, { id, name }]);
    setCurrentFolder(id);
  };
  const navigateUp = (idx: number) => {
    if (idx < 0) { setFolderPath([]); setCurrentFolder(undefined); }
    else { setFolderPath(folderPath.slice(0, idx + 1)); setCurrentFolder(folderPath[idx].id); }
  };

  const handleCreateFolder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!folderName) return;
    await createFolder({ project_id: projectId, parent_id: currentFolder || null, name: folderName });
    setFolderName(""); setShowNewFolder(false); rFolders();
  };

  const performUpload = async (file: File, expiry: string) => {
    const token = localStorage.getItem("token");
    const fd = new FormData();
    fd.append("file", file);
    fd.append("title", file.name);
    fd.append("project_id", projectId || "null");
    fd.append("folder_id", currentFolder || "null");
    if (expiry) fd.append("expiry_date", expiry);
    await fetch(`${API_URL}/api/dms/documents`, {
      method: "POST", headers: { Authorization: `Bearer ${token}` }, body: fd,
    });
    rDocs();
  };

  const handleFileSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPendingUpload(file);
    e.target.value = "";
  };

  const submitPendingUpload = async () => {
    if (!pendingUpload) return;
    await performUpload(pendingUpload, uploadExpiry);
    setPendingUpload(null);
    setUploadExpiry("");
  };

  return (
    <div>
      <PageHeader title="Files" subtitle="Browse folders, upload files, manage versions and sharing." />
      <CommandBar
        items={[
          { key: "new-folder", label: "New folder", onClick: () => setShowNewFolder(true) },
          {
            key: "upload", label: "Upload file", variant: "primary",
            onClick: () => document.getElementById("dms-upload-input")?.click(),
          },
        ]}
        right={
          <input id="dms-upload-input" type="file" onChange={handleFileSelected} style={{ display: "none" }} />
        }
      />

      {expiring.length > 0 && (
        <div className="card" style={{ marginBottom: "1rem", borderLeft: "3px solid var(--warning)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.4rem" }}>
            <b>Expiring soon ({expiring.length})</b>
            <span style={{ fontSize: "0.75rem", color: "var(--gray-500)" }}>within 30 days</span>
          </div>
          {expiring.slice(0, 5).map((d: any) => (
            <div key={d.id} style={{ fontSize: "0.85rem", padding: "0.2rem 0", display: "flex", justifyContent: "space-between" }}>
              <span>{d.title}</span>
              <span style={{ color: "var(--warning)" }}>{new Date(d.expiry_date).toLocaleDateString()}</span>
            </div>
          ))}
        </div>
      )}

      {/* Upload modal — asks for optional expiry */}
      {pendingUpload && (
        <div className="modal-overlay" onClick={() => setPendingUpload(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Upload {pendingUpload.name}</h3>
            <div style={{ fontSize: "0.82rem", color: "var(--gray-500)", marginBottom: "0.75rem" }}>
              {formatSize(pendingUpload.size)} · {pendingUpload.type || "unknown type"}
            </div>
            <div className="form-group">
              <label>Expiry date (optional)</label>
              <input type="date" value={uploadExpiry} onChange={(e) => setUploadExpiry(e.target.value)} />
            </div>
            <div className="modal-actions">
              <button className="btn" onClick={() => setPendingUpload(null)}>Cancel</button>
              <button className="btn btn-primary" onClick={submitPendingUpload}>Upload</button>
            </div>
          </div>
        </div>
      )}

      <div className="card" style={{ marginBottom: "1rem", padding: "0.75rem 1rem" }}>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <input value={searchQ} onChange={(e) => setSearchQ(e.target.value)} placeholder="Search documents..." style={{ flex: 1, padding: "0.45rem 0.65rem", border: "1px solid var(--gray-300)", borderRadius: "var(--radius)", fontSize: "0.85rem" }} />
          <label style={{ fontSize: "0.75rem", display: "flex", alignItems: "center", gap: "0.25rem", whiteSpace: "nowrap" }}>
            <input type="checkbox" checked={fullText} onChange={(e) => setFullText(e.target.checked)} /> Full text
          </label>
          <button className="btn btn-sm" onClick={() => setShowFilters((x) => !x)}>{showFilters ? "Hide" : "Filters"}</button>
        </div>

        {showFilters && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "0.5rem", marginTop: "0.75rem" }}>
            <label style={{ fontSize: "0.72rem", color: "var(--gray-500)" }}>
              From
              <input type="date" value={fDateFrom} onChange={(e) => setFDateFrom(e.target.value)} style={{ width: "100%" }} />
            </label>
            <label style={{ fontSize: "0.72rem", color: "var(--gray-500)" }}>
              To
              <input type="date" value={fDateTo} onChange={(e) => setFDateTo(e.target.value)} style={{ width: "100%" }} />
            </label>
            <label style={{ fontSize: "0.72rem", color: "var(--gray-500)" }}>
              Status
              <select value={fStatus} onChange={(e) => setFStatus(e.target.value)} style={{ width: "100%" }}>
                <option value="">any</option>
                <option value="draft">draft</option>
                <option value="review">review</option>
                <option value="approved">approved</option>
                <option value="archived">archived</option>
              </select>
            </label>
            <label style={{ fontSize: "0.72rem", color: "var(--gray-500)" }}>
              File type
              <select value={fType} onChange={(e) => setFType(e.target.value)} style={{ width: "100%" }}>
                <option value="">any</option>
                <option value="application/pdf">PDF</option>
                <option value="image/">images</option>
                <option value="text/">text</option>
                <option value="application/vnd.openxmlformats">Office</option>
              </select>
            </label>
            <label style={{ fontSize: "0.72rem", color: "var(--gray-500)" }}>
              Author ID
              <input type="text" value={fAuthor} onChange={(e) => setFAuthor(e.target.value)} placeholder="uuid" style={{ width: "100%" }} />
            </label>
          </div>
        )}

        {searchQ.length >= 2 && searchResults.length > 0 && (
          <div style={{ marginTop: "0.5rem" }}>
            {searchResults.map((d: any) => (
              <div key={d.id} style={{ padding: "0.4rem 0", borderBottom: "1px solid var(--gray-100)", fontSize: "0.85rem", display: "flex", justifyContent: "space-between" }}>
                <span style={{ fontWeight: 500 }}>{d.title}</span>
                <div>
                  <span className="badge badge-blue">{d.status}</span>
                  {d.tags && <span className="badge badge-gray">{d.tags}</span>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card" style={{ marginBottom: "1rem", padding: "0.75rem 1rem" }}>
        <div style={{ display: "flex", gap: "0.25rem", alignItems: "center", fontSize: "0.85rem" }}>
          <button onClick={() => navigateUp(-1)} style={{ background: "none", border: "none", cursor: "pointer", fontWeight: 600, color: "var(--primary)" }}>Root</button>
          {folderPath.map((f, i) => (
            <span key={f.id}>
              <span style={{ color: "var(--gray-400)", margin: "0 0.25rem" }}>/</span>
              <button onClick={() => navigateUp(i)} style={{ background: "none", border: "none", cursor: "pointer", fontWeight: 500, color: "var(--primary)" }}>{f.name}</button>
            </span>
          ))}
        </div>
      </div>

      {showNewFolder && (
        <div className="card" style={{ marginBottom: "1rem", padding: "0.75rem 1rem" }}>
          <form onSubmit={handleCreateFolder} style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <input value={folderName} onChange={(e) => setFolderName(e.target.value)} placeholder="Folder name" required autoFocus style={{ flex: 1, padding: "0.4rem 0.6rem", border: "1px solid var(--gray-300)", borderRadius: "var(--radius)", fontSize: "0.85rem" }} />
            <button type="submit" className="btn btn-primary btn-sm">Create</button>
            <button type="button" className="btn btn-sm" onClick={() => setShowNewFolder(false)}>Cancel</button>
          </form>
        </div>
      )}

      {folders.length > 0 && (
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "1rem" }}>
          {folders.map((f: any) => (
            <div key={f.id} style={{ padding: "0.75rem 1rem", background: "white", border: "1px solid var(--gray-200)", borderRadius: "var(--radius-lg)", display: "flex", alignItems: "center", gap: "0.5rem", minWidth: 220 }} className="project-card">
              <span style={{ fontSize: "1.3rem", cursor: "pointer" }} onClick={() => navigateToFolder(f.id, f.name)}>&#128193;</span>
              <div style={{ flex: 1, cursor: "pointer" }} onClick={() => navigateToFolder(f.id, f.name)}>
                <div style={{ fontWeight: 600, fontSize: "0.85rem" }}>{f.name}</div>
                <div style={{ fontSize: "0.72rem", color: "var(--gray-500)" }}>{f.doc_count} docs, {f.subfolder_count} folders</div>
              </div>
              <button
                className="btn btn-sm"
                title="Manage permissions"
                onClick={(e) => { e.stopPropagation(); setPermFolder({ id: f.id, name: f.name }); }}
                style={{ fontSize: "0.68rem", padding: "0.25rem 0.5rem" }}
              >
                Perms
              </button>
            </div>
          ))}
        </div>
      )}

      {docs.length > 0 ? (
        <div className="card">
          <table>
            <thead><tr><th>Title</th><th>Status</th><th>Version</th><th>Tags</th><th>Expiry</th><th>Updated</th><th>Actions</th></tr></thead>
            <tbody>
              {docs.map((d: any) => (
                <tr key={d.id}>
                  <td style={{ fontWeight: 500 }}>{d.title}</td>
                  <td><span className={`badge ${d.status === "approved" ? "badge-green" : d.status === "review" ? "badge-yellow" : "badge-gray"}`}>{d.status}</span></td>
                  <td>v{d.current_version}</td>
                  <td>{d.tags ? d.tags.split(",").map((t: string) => <span key={t} className="badge badge-gray" style={{ marginRight: "0.2rem" }}>{t.trim()}</span>) : "-"}</td>
                  <td style={{ fontSize: "0.75rem" }}>{d.expiry_date ? new Date(d.expiry_date).toLocaleDateString() : "-"}</td>
                  <td style={{ fontSize: "0.82rem" }}>{new Date(d.updated_at).toLocaleDateString()}</td>
                  <td>
                    <div style={{ display: "flex", gap: "0.25rem", flexWrap: "wrap" }}>
                      <a href={`${API_URL}/api/dms/documents/${d.id}/download`} className="btn btn-sm btn-primary" style={{ textDecoration: "none", fontSize: "0.72rem" }} target="_blank" rel="noreferrer">Download</a>
                      <button className="btn btn-sm" onClick={() => setVersionDocId(versionDocId === d.id ? null : d.id)}>Versions</button>
                      <button className="btn btn-sm" onClick={() => setShareDocId(d.id)}>Share</button>
                      <button className="btn btn-sm" onClick={async () => { try { await checkoutDoc({ id: d.id, body: {} }).unwrap(); alert("Checked out"); } catch (err: any) { alert(err?.data?.detail || "Failed"); } }}>Checkout</button>
                      <button className="btn btn-sm" onClick={async () => { await checkinDoc(d.id); alert("Checked in"); }}>Check-in</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : folders.length === 0 && (
        <div className="empty-state"><p>This folder is empty. Upload a file or create a subfolder.</p></div>
      )}

      {versionDocId && versions.length > 0 && (
        <div className="card" style={{ marginTop: "1rem" }}>
          <h3 style={{ marginBottom: "0.75rem" }}>Version history</h3>
          <table>
            <thead><tr><th>Version</th><th>File</th><th>Size</th><th>Notes</th><th>Date</th><th>Actions</th></tr></thead>
            <tbody>
              {versions.map((v: any, i: number) => (
                <tr key={v.id}>
                  <td style={{ fontWeight: 600 }}>v{v.version}</td>
                  <td>{v.original_name}</td>
                  <td>{v.size_bytes ? formatSize(v.size_bytes) : "-"}</td>
                  <td style={{ fontSize: "0.82rem", color: "var(--gray-500)" }}>{v.change_notes || "-"}</td>
                  <td style={{ fontSize: "0.82rem" }}>{new Date(v.created_at).toLocaleDateString()}</td>
                  <td style={{ display: "flex", gap: "0.25rem" }}>
                    <a href={`${API_URL}/api/dms/documents/${versionDocId}/download?version=${v.version}`} className="btn btn-sm" style={{ textDecoration: "none", fontSize: "0.72rem" }} target="_blank" rel="noreferrer">Download</a>
                    {i !== 0 && (
                      <button className="btn btn-sm" onClick={async () => {
                        if (!confirm(`Restore v${v.version} as the current version? This creates a new version copying its contents.`)) return;
                        await restoreVersion({ docId: versionDocId, version: v.version });
                        rVersions(); rDocs();
                      }}>Restore</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {shareDocId && <ShareDialog docId={shareDocId} onClose={() => setShareDocId(null)} />}
      {permFolder && <FolderPermissionsDialog folder={permFolder} onClose={() => setPermFolder(null)} />}
    </div>
  );
}

// ── Share dialog ──────────────────────────────────────────────────

function ShareDialog({ docId, onClose }: { docId: string; onClose: () => void }) {
  const { data: links = [], refetch } = useGetDocShareLinksQuery(docId);
  const [createLink] = useCreateDocShareLinkMutation();
  const [revokeLink] = useRevokeDocShareLinkMutation();
  const [days, setDays] = useState<number | "">(7);

  const publicUrl = (token: string) =>
    `${window.location.origin}/api/dms/share/${token}`;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ minWidth: 520 }}>
        <h3>Share links</h3>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "end", marginBottom: "1rem" }}>
          <label style={{ fontSize: "0.75rem", color: "var(--gray-500)", flex: 1 }}>
            Expires in (days, blank = no expiry)
            <input
              type="number"
              value={days}
              onChange={(e) => setDays(e.target.value === "" ? "" : Number(e.target.value))}
              min={1} max={365}
              style={{ width: "100%" }}
            />
          </label>
          <button
            className="btn btn-primary btn-sm"
            onClick={async () => {
              await createLink({ docId, expires_in_days: days === "" ? null : days });
              refetch();
            }}
          >
            + Create link
          </button>
        </div>

        {links.length === 0 ? (
          <div style={{ color: "var(--gray-500)", fontSize: "0.85rem" }}>No share links yet.</div>
        ) : (
          <table>
            <thead>
              <tr><th>URL</th><th>Expires</th><th>Downloads</th><th>Status</th><th></th></tr>
            </thead>
            <tbody>
              {links.map((l: any) => (
                <tr key={l.id}>
                  <td style={{ fontFamily: "monospace", fontSize: "0.72rem", maxWidth: 240, overflow: "hidden", textOverflow: "ellipsis" }}>
                    {publicUrl(l.token)}
                  </td>
                  <td style={{ fontSize: "0.82rem" }}>{l.expires_at ? new Date(l.expires_at).toLocaleDateString() : "never"}</td>
                  <td>{l.download_count}</td>
                  <td>{l.is_revoked ? <span className="badge badge-red">revoked</span> : <span className="badge badge-green">active</span>}</td>
                  <td style={{ display: "flex", gap: "0.25rem" }}>
                    <button className="btn btn-sm" onClick={() => navigator.clipboard.writeText(publicUrl(l.token))}>Copy</button>
                    {!l.is_revoked && (
                      <button className="btn btn-sm btn-danger" onClick={async () => { await revokeLink(l.id); refetch(); }}>Revoke</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="modal-actions">
          <button className="btn" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}

// ── Folder permissions dialog ────────────────────────────────────

function FolderPermissionsDialog({ folder, onClose }: { folder: { id: string; name: string }; onClose: () => void }) {
  const { data: perms = [], refetch } = useGetFolderPermissionsQuery(folder.id);
  const { data: users = [] } = useGetAdminUsersQuery();
  const [addPerm] = useGrantFolderPermissionMutation();
  const [removePerm] = useRevokeFolderPermissionMutation();
  const [userId, setUserId] = useState("");
  const [permission, setPermission] = useState("read");

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ minWidth: 520 }}>
        <h3>Permissions — {folder.name}</h3>
        <div style={{ fontSize: "0.78rem", color: "var(--gray-500)", marginBottom: "0.75rem" }}>
          Folders with no explicit permissions are visible to everyone. Adding any
          permission converts the folder to private — only listed users (plus admins
          and the creator) can see it.
        </div>

        <div style={{ display: "flex", gap: "0.5rem", alignItems: "end", marginBottom: "1rem" }}>
          <label style={{ fontSize: "0.75rem", color: "var(--gray-500)", flex: 2 }}>
            User
            <select value={userId} onChange={(e) => setUserId(e.target.value)} style={{ width: "100%" }}>
              <option value="">— select user —</option>
              {users.map((u: any) => <option key={u.id} value={u.id}>{u.name || u.email}</option>)}
            </select>
          </label>
          <label style={{ fontSize: "0.75rem", color: "var(--gray-500)", flex: 1 }}>
            Level
            <select value={permission} onChange={(e) => setPermission(e.target.value)} style={{ width: "100%" }}>
              <option value="read">read</option>
              <option value="write">write</option>
              <option value="admin">admin</option>
            </select>
          </label>
          <button
            className="btn btn-primary btn-sm"
            disabled={!userId}
            onClick={async () => {
              await addPerm({ folder_id: folder.id, user_id: userId, permission });
              setUserId(""); refetch();
            }}
          >
            + Add
          </button>
        </div>

        {perms.length === 0 ? (
          <div style={{ color: "var(--gray-500)", fontSize: "0.85rem" }}>No explicit permissions — folder is public.</div>
        ) : (
          <table>
            <thead><tr><th>User</th><th>Level</th><th></th></tr></thead>
            <tbody>
              {perms.map((p: any) => {
                const user = users.find((u: any) => u.id === p.user_id);
                return (
                  <tr key={p.id}>
                    <td>{user ? (user.name || user.email) : <span style={{ fontFamily: "monospace", fontSize: "0.72rem" }}>{p.user_id.slice(0, 8)}…</span>}</td>
                    <td><span className="badge badge-blue">{p.permission}</span></td>
                    <td>
                      <button className="btn btn-sm btn-danger" onClick={async () => { await removePerm(p.id); refetch(); }}>Remove</button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
        <div className="modal-actions">
          <button className="btn" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}
