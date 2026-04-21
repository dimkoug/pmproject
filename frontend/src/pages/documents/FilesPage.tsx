import { useState } from "react";
import {
  useGetFoldersQuery, useCreateFolderMutation,
  useGetDocumentsQuery, useGetDocVersionsQuery, useSearchDocumentsQuery,
  useCheckoutDocMutation, useCheckinDocMutation,
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
  const [createFolder] = useCreateFolderMutation();
  const [searchQ, setSearchQ] = useState("");
  const [fullText, setFullText] = useState(false);
  const { data: searchResults = [] } = useSearchDocumentsQuery({ q: searchQ, fullText }, { skip: searchQ.length < 2 });
  const [checkoutDoc] = useCheckoutDocMutation();
  const [checkinDoc] = useCheckinDocMutation();
  const [showNewFolder, setShowNewFolder] = useState(false);
  const [folderName, setFolderName] = useState("");
  const [versionDocId, setVersionDocId] = useState<string | null>(null);
  const { data: versions = [] } = useGetDocVersionsQuery(versionDocId!, { skip: !versionDocId });

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

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const token = localStorage.getItem("token");
    const fd = new FormData();
    fd.append("file", file);
    fd.append("title", file.name);
    fd.append("project_id", projectId || "null");
    fd.append("folder_id", currentFolder || "null");
    await fetch(`${API_URL}/api/dms/documents`, {
      method: "POST", headers: { Authorization: `Bearer ${token}` }, body: fd,
    });
    rDocs();
    e.target.value = "";
  };

  return (
    <div>
      <PageHeader title="Files" subtitle="Browse folders, upload files, and manage versions." />
      <CommandBar
        items={[
          { key: "new-folder", label: "New folder", onClick: () => setShowNewFolder(true) },
          {
            key: "upload", label: "Upload file", variant: "primary",
            onClick: () => document.getElementById("dms-upload-input")?.click(),
          },
        ]}
        right={
          <label htmlFor="dms-upload-input" style={{ display: "none" }}>
            <input id="dms-upload-input" type="file" onChange={handleUpload} style={{ display: "none" }} />
          </label>
        }
      />

      <div className="card" style={{ marginBottom: "1rem", padding: "0.75rem 1rem" }}>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <input value={searchQ} onChange={(e) => setSearchQ(e.target.value)} placeholder="Search documents..." style={{ flex: 1, padding: "0.45rem 0.65rem", border: "1px solid var(--gray-300)", borderRadius: "var(--radius)", fontSize: "0.85rem" }} />
          <label style={{ fontSize: "0.75rem", display: "flex", alignItems: "center", gap: "0.25rem", whiteSpace: "nowrap" }}>
            <input type="checkbox" checked={fullText} onChange={(e) => setFullText(e.target.checked)} /> Full text
          </label>
        </div>
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
            <div key={f.id} onClick={() => navigateToFolder(f.id, f.name)} style={{ cursor: "pointer", padding: "0.75rem 1rem", background: "white", border: "1px solid var(--gray-200)", borderRadius: "var(--radius-lg)", display: "flex", alignItems: "center", gap: "0.5rem", minWidth: 180 }} className="project-card">
              <span style={{ fontSize: "1.3rem" }}>&#128193;</span>
              <div>
                <div style={{ fontWeight: 600, fontSize: "0.85rem" }}>{f.name}</div>
                <div style={{ fontSize: "0.72rem", color: "var(--gray-500)" }}>{f.doc_count} docs, {f.subfolder_count} folders</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {docs.length > 0 ? (
        <div className="card">
          <table>
            <thead><tr><th>Title</th><th>Status</th><th>Version</th><th>Tags</th><th>Updated</th><th>Actions</th></tr></thead>
            <tbody>
              {docs.map((d: any) => (
                <tr key={d.id}>
                  <td style={{ fontWeight: 500 }}>{d.title}</td>
                  <td><span className={`badge ${d.status === "approved" ? "badge-green" : d.status === "review" ? "badge-yellow" : "badge-gray"}`}>{d.status}</span></td>
                  <td>v{d.current_version}</td>
                  <td>{d.tags ? d.tags.split(",").map((t: string) => <span key={t} className="badge badge-gray" style={{ marginRight: "0.2rem" }}>{t.trim()}</span>) : "-"}</td>
                  <td style={{ fontSize: "0.82rem" }}>{new Date(d.updated_at).toLocaleDateString()}</td>
                  <td>
                    <div style={{ display: "flex", gap: "0.25rem", flexWrap: "wrap" }}>
                      <a href={`${API_URL}/api/dms/documents/${d.id}/download`} className="btn btn-sm btn-primary" style={{ textDecoration: "none", fontSize: "0.72rem" }} target="_blank" rel="noreferrer">Download</a>
                      <button className="btn btn-sm" onClick={() => setVersionDocId(versionDocId === d.id ? null : d.id)}>Versions</button>
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
            <thead><tr><th>Version</th><th>File</th><th>Size</th><th>Notes</th><th>Date</th><th>Download</th></tr></thead>
            <tbody>
              {versions.map((v: any) => (
                <tr key={v.id}>
                  <td style={{ fontWeight: 600 }}>v{v.version}</td>
                  <td>{v.original_name}</td>
                  <td>{v.size_bytes ? formatSize(v.size_bytes) : "-"}</td>
                  <td style={{ fontSize: "0.82rem", color: "var(--gray-500)" }}>{v.change_notes || "-"}</td>
                  <td style={{ fontSize: "0.82rem" }}>{new Date(v.created_at).toLocaleDateString()}</td>
                  <td><a href={`${API_URL}/api/dms/documents/${versionDocId}/download?version=${v.version}`} className="btn btn-sm" style={{ textDecoration: "none", fontSize: "0.72rem" }} target="_blank" rel="noreferrer">Download</a></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
