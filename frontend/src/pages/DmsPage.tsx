import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  useGetDmsDashboardQuery, useGetFoldersQuery, useCreateFolderMutation,
  useGetDocumentsQuery, useGetDocVersionsQuery, useSearchDocumentsQuery,
  useGetSignaturesQuery, useCreateSignatureMutation,
  useGetDmsTemplatesQuery, useCreateDmsTemplateMutation, useInstantiateTemplateMutation,
  useGetRetentionPoliciesQuery, useCreateRetentionPolicyMutation, useApplyRetentionMutation,
  useCheckoutDocMutation, useCheckinDocMutation, useGetLocksQuery,
  useGetWorkflowsQuery, useCreateWorkflowMutation, useAdvanceWorkflowMutation,
  useGetAnnotationsQuery, useCreateAnnotationMutation, useResolveAnnotationMutation,
  useGetScanResultsQuery, useScanVersionMutation,
} from "../services/api";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const DMS_TABS = ["files", "signatures", "templates", "retention", "locks", "workflows", "annotations", "scans"] as const;

export default function DmsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [tab, setTab] = useState<typeof DMS_TABS[number]>("files");
  const [currentFolder, setCurrentFolder] = useState<string | undefined>(undefined);
  const [folderPath, setFolderPath] = useState<{id: string; name: string}[]>([]);
  const { data: dash } = useGetDmsDashboardQuery(projectId);
  const { data: folders = [], refetch: rFolders } = useGetFoldersQuery({ projectId, parentId: currentFolder });
  const { data: docs = [], refetch: rDocs } = useGetDocumentsQuery({ folderId: currentFolder, projectId });
  const [createFolder] = useCreateFolderMutation();
  const [searchQ, setSearchQ] = useState("");
  const [fullText, setFullText] = useState(false);
  const { data: searchResults = [] } = useSearchDocumentsQuery({ q: searchQ, fullText }, { skip: searchQ.length < 2 });
  const { data: sigs = [], refetch: rSigs } = useGetSignaturesQuery();
  const [createSig] = useCreateSignatureMutation();
  const { data: templates = [], refetch: rTpls } = useGetDmsTemplatesQuery();
  const [createTpl] = useCreateDmsTemplateMutation();
  const [instantiateTpl] = useInstantiateTemplateMutation();
  const { data: policies = [], refetch: rPols } = useGetRetentionPoliciesQuery();
  const [createPolicy] = useCreateRetentionPolicyMutation();
  const [applyRetention] = useApplyRetentionMutation();
  const [checkoutDoc] = useCheckoutDocMutation();
  const [checkinDoc] = useCheckinDocMutation();
  const { data: locks = [], refetch: rLocks } = useGetLocksQuery(undefined, { skip: tab !== "locks" });
  const { data: workflows = [], refetch: rWf } = useGetWorkflowsQuery(undefined, { skip: tab !== "workflows" });
  const [createWorkflow] = useCreateWorkflowMutation();
  const [advanceWorkflow] = useAdvanceWorkflowMutation();
  const [annotationDocId, setAnnotationDocId] = useState<string | null>(null);
  const { data: annotations = [], refetch: rAnn } = useGetAnnotationsQuery(annotationDocId!, { skip: !annotationDocId });
  const [createAnn] = useCreateAnnotationMutation();
  const [resolveAnn] = useResolveAnnotationMutation();
  const { data: scans = [], refetch: rScans } = useGetScanResultsQuery(undefined, { skip: tab !== "scans" });
  const [scanVersion] = useScanVersionMutation();
  const [showNewFolder, setShowNewFolder] = useState(false);
  const [folderName, setFolderName] = useState("");
  const [versionDocId, setVersionDocId] = useState<string | null>(null);
  const { data: versions = [] } = useGetDocVersionsQuery(versionDocId!, { skip: !versionDocId });

  const navigateToFolder = (folderId: string, folderName: string) => {
    setFolderPath([...folderPath, { id: folderId, name: folderName }]);
    setCurrentFolder(folderId);
  };

  const navigateUp = (idx: number) => {
    if (idx < 0) {
      setFolderPath([]);
      setCurrentFolder(undefined);
    } else {
      setFolderPath(folderPath.slice(0, idx + 1));
      setCurrentFolder(folderPath[idx].id);
    }
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

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };

  return (
    <div>
      <div style={{ marginBottom: "1.5rem" }}>
        <h2 style={{ fontSize: "1.4rem", fontWeight: 700, marginBottom: "0.3rem" }}>Document Management</h2>
        <p style={{ color: "var(--gray-400)", fontSize: "0.85rem" }}>Organized document storage with version control</p>
      </div>

      {dash && (
        <div className="stats-grid" style={{ marginBottom: "1.25rem" }}>
          <div className="stat-card"><div className="label">Documents</div><div className="value">{dash.documents}</div></div>
          <div className="stat-card"><div className="label">Folders</div><div className="value">{dash.folders}</div></div>
          <div className="stat-card"><div className="label">Versions</div><div className="value">{dash.versions}</div></div>
          <div className="stat-card"><div className="label">Total Size</div><div className="value">{dash.total_size_mb} MB</div></div>
        </div>
      )}

      <div style={{ display: "flex", gap: "0.35rem", marginBottom: "1rem", flexWrap: "wrap" }}>
        {DMS_TABS.map(t => <button key={t} className={`btn btn-sm ${tab === t ? "btn-primary" : ""}`} onClick={() => setTab(t)}>{t.charAt(0).toUpperCase() + t.slice(1)}</button>)}
      </div>

      {tab === "signatures" && (
        <div className="card">
          <div className="card-header"><h3>E-Signature Requests</h3>
            <button className="btn btn-sm btn-primary" onClick={async () => {
              const docId = prompt("Document ID:"); const email = prompt("Signer email:");
              if (docId && email) { await createSig({ document_id: docId, signer_email: email }); rSigs(); }
            }}>+ Request</button>
          </div>
          <table><thead><tr><th>Signer</th><th>Document</th><th>Status</th><th>Signed</th><th>Link</th></tr></thead><tbody>
            {sigs.map((s: any) => <tr key={s.id}>
              <td>{s.signer_email}</td><td style={{ fontSize: "0.75rem" }}>{s.document_id.slice(0, 8)}…</td>
              <td><span className={`badge ${s.status === "signed" ? "badge-green" : s.status === "declined" ? "badge-red" : "badge-yellow"}`}>{s.status}</span></td>
              <td>{s.signed_at ? new Date(s.signed_at).toLocaleDateString() : "-"}</td>
              <td style={{ fontSize: "0.72rem", fontFamily: "monospace" }}>{s.token?.slice(0, 16)}…</td>
            </tr>)}
          </tbody></table>
        </div>
      )}

      {tab === "templates" && (
        <div className="card">
          <div className="card-header"><h3>Document Templates</h3>
            <button className="btn btn-sm btn-primary" onClick={async () => {
              const name = prompt("Template name:"); if (!name) return;
              const body = prompt("Body (use {{var}} placeholders):"); if (!body) return;
              await createTpl({ name, body }); rTpls();
            }}>+ New</button>
          </div>
          <table><thead><tr><th>Name</th><th>Category</th><th>Description</th><th>Actions</th></tr></thead><tbody>
            {templates.map((t: any) => <tr key={t.id}>
              <td style={{ fontWeight: 500 }}>{t.name}</td>
              <td>{t.category || "-"}</td>
              <td style={{ fontSize: "0.82rem", color: "var(--gray-500)" }}>{t.description || "-"}</td>
              <td><button className="btn btn-sm" onClick={async () => {
                const title = prompt("New document title:"); if (!title) return;
                await instantiateTpl({ templateId: t.id, body: { title, project_id: projectId, vars: {} } });
                rDocs();
              }}>Instantiate</button></td>
            </tr>)}
          </tbody></table>
        </div>
      )}

      {tab === "retention" && (
        <div className="card">
          <div className="card-header"><h3>Retention Policies</h3>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button className="btn btn-sm" onClick={async () => { const r: any = await applyRetention(); alert(`Archived ${r.data?.archived || 0}, deleted ${r.data?.deleted || 0}`); rPols(); rDocs(); }}>Apply Now</button>
              <button className="btn btn-sm btn-primary" onClick={async () => {
                const name = prompt("Policy name:"); if (!name) return;
                const days = parseInt(prompt("Days after last update:") || "0"); if (!days) return;
                const action = prompt("Action (archive/delete):", "archive") || "archive";
                await createPolicy({ name, days_after: days, action }); rPols();
              }}>+ New</button>
            </div>
          </div>
          <table><thead><tr><th>Name</th><th>Folder / Tag</th><th>Days</th><th>Action</th><th>Active</th></tr></thead><tbody>
            {policies.map((p: any) => <tr key={p.id}>
              <td style={{ fontWeight: 500 }}>{p.name}</td>
              <td style={{ fontSize: "0.82rem" }}>{p.tag_match ? `tag: ${p.tag_match}` : p.folder_id ? "folder" : "all"}</td>
              <td>{p.days_after}</td>
              <td><span className="badge badge-blue">{p.action}</span></td>
              <td>{p.is_active ? <span className="badge badge-green">Yes</span> : <span className="badge badge-gray">No</span>}</td>
            </tr>)}
          </tbody></table>
        </div>
      )}

      {tab === "locks" && (
        <div className="card">
          <div className="card-header"><h3>Active Locks</h3></div>
          <table><thead><tr><th>Document</th><th>User</th><th>Locked At</th><th>Note</th><th>Actions</th></tr></thead><tbody>
            {locks.map((l: any) => <tr key={l.document_id}>
              <td style={{ fontWeight: 500 }}>{l.title || l.document_id.slice(0, 8) + "…"}</td>
              <td style={{ fontSize: "0.75rem" }}>{l.user_id.slice(0, 8)}…</td>
              <td style={{ fontSize: "0.82rem" }}>{l.locked_at ? new Date(l.locked_at).toLocaleString() : ""}</td>
              <td style={{ fontSize: "0.82rem" }}>{l.note || "-"}</td>
              <td><button className="btn btn-sm" onClick={async () => { await checkinDoc(l.document_id); rLocks(); }}>Force Check-in</button></td>
            </tr>)}
            {locks.length === 0 && <tr><td colSpan={5} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No active locks.</td></tr>}
          </tbody></table>
        </div>
      )}

      {tab === "workflows" && (
        <div className="card">
          <div className="card-header"><h3>Document Workflows</h3>
            <button className="btn btn-sm btn-primary" onClick={async () => {
              const docId = prompt("Document ID:"); if (!docId) return;
              const name = prompt("Workflow name:") || "Review";
              await createWorkflow({ document_id: docId, name, steps: [
                { step_order: 0, role: "author" },
                { step_order: 1, role: "reviewer" },
                { step_order: 2, role: "approver" },
              ]});
              rWf();
            }}>+ New Workflow</button>
          </div>
          {workflows.map((w: any) => (
            <div key={w.id} style={{ padding: "0.75rem 1rem", borderTop: "1px solid var(--gray-100)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div><b>{w.name}</b> <span style={{ fontSize: "0.75rem", color: "var(--gray-500)", marginLeft: "0.5rem" }}>{w.document_id.slice(0, 8)}…</span></div>
                <span className={`badge ${w.is_complete ? "badge-green" : "badge-yellow"}`}>{w.is_complete ? "Complete" : `Step ${w.current_step + 1}`}</span>
              </div>
              <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem", flexWrap: "wrap" }}>
                {w.steps.map((s: any, i: number) => (
                  <div key={s.id} style={{ padding: "0.3rem 0.6rem", border: `1px solid var(--gray-${s.status === "pending" ? "300" : "200"})`, borderRadius: 4, fontSize: "0.78rem", background: s.status === "approved" ? "#d1fae5" : s.status === "rejected" ? "#fee2e2" : i === w.current_step ? "#fef3c7" : "white" }}>
                    {s.role} {s.status !== "pending" && `(${s.status})`}
                  </div>
                ))}
              </div>
              {!w.is_complete && (
                <div style={{ display: "flex", gap: "0.25rem", marginTop: "0.5rem" }}>
                  <button className="btn btn-sm btn-primary" onClick={async () => { await advanceWorkflow({ id: w.id, body: { decision: "approved" } }); rWf(); }}>Approve Step</button>
                  <button className="btn btn-sm" onClick={async () => { const n = prompt("Reason:") || ""; await advanceWorkflow({ id: w.id, body: { decision: "rejected", note: n } }); rWf(); }}>Reject</button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {tab === "annotations" && (
        <div className="card">
          <div className="card-header"><h3>Annotations</h3>
            <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <input placeholder="Document ID" value={annotationDocId || ""} onChange={e => setAnnotationDocId(e.target.value || null)} style={{ padding: "0.3rem 0.5rem", border: "1px solid var(--gray-300)", borderRadius: 4, fontSize: "0.82rem" }} />
              <button className="btn btn-sm btn-primary" disabled={!annotationDocId} onClick={async () => {
                const body = prompt("Comment:"); if (!body || !annotationDocId) return;
                await createAnn({ document_id: annotationDocId, body });
                rAnn();
              }}>+ Comment</button>
            </div>
          </div>
          {annotationDocId && annotations.map((a: any) => (
            <div key={a.id} style={{ padding: "0.5rem 1rem", borderTop: "1px solid var(--gray-100)", display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.5rem" }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: "0.85rem", fontWeight: a.resolved ? 400 : 500, textDecoration: a.resolved ? "line-through" : "none" }}>{a.body}</div>
                <div style={{ fontSize: "0.72rem", color: "var(--gray-500)" }}>{a.author_id?.slice(0, 8)}… · {a.created_at ? new Date(a.created_at).toLocaleString() : ""}</div>
              </div>
              {!a.resolved && <button className="btn btn-sm" onClick={async () => { await resolveAnn(a.id); rAnn(); }}>Resolve</button>}
            </div>
          ))}
        </div>
      )}

      {tab === "scans" && (
        <div className="card">
          <div className="card-header"><h3>Virus Scan Results</h3>
            <button className="btn btn-sm" onClick={async () => {
              const vid = prompt("Version ID to scan:"); if (!vid) return;
              const r: any = await scanVersion(vid);
              alert(`Status: ${r.data?.status}${r.data?.details ? " — " + r.data.details : ""}`);
              rScans();
            }}>Scan Version</button>
          </div>
          <table><thead><tr><th>Version</th><th>Status</th><th>Details</th><th>Scanned At</th></tr></thead><tbody>
            {scans.map((s: any) => <tr key={s.id}>
              <td style={{ fontSize: "0.75rem" }}>{s.version_id.slice(0, 8)}…</td>
              <td><span className={`badge ${s.status === "clean" ? "badge-green" : s.status === "infected" ? "badge-red" : "badge-gray"}`}>{s.status}</span></td>
              <td style={{ fontSize: "0.82rem" }}>{s.details || "—"}</td>
              <td style={{ fontSize: "0.82rem" }}>{s.scanned_at ? new Date(s.scanned_at).toLocaleString() : ""}</td>
            </tr>)}
          </tbody></table>
        </div>
      )}

      {tab === "files" && <>
      {/* Search */}
      <div className="card" style={{ marginBottom: "1rem", padding: "0.75rem 1rem" }}>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <input value={searchQ} onChange={e => setSearchQ(e.target.value)} placeholder="Search documents..." style={{ flex: 1, padding: "0.45rem 0.65rem", border: "1px solid var(--gray-300)", borderRadius: "var(--radius)", fontSize: "0.85rem", fontFamily: "var(--font-sans)" }} />
          <label style={{ fontSize: "0.75rem", display: "flex", alignItems: "center", gap: "0.25rem", whiteSpace: "nowrap" }}>
            <input type="checkbox" checked={fullText} onChange={e => setFullText(e.target.checked)} /> Full text
          </label>
        </div>
        {searchQ.length >= 2 && searchResults.length > 0 && (
          <div style={{ marginTop: "0.5rem" }}>
            {searchResults.map((d: any) => (
              <div key={d.id} style={{ padding: "0.4rem 0", borderBottom: "1px solid var(--gray-100)", fontSize: "0.85rem", display: "flex", justifyContent: "space-between" }}>
                <span style={{ fontWeight: 500 }}>{d.title}</span>
                <div><span className="badge badge-blue">{d.status}</span> {d.tags && <span className="badge badge-gray">{d.tags}</span>}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Breadcrumbs + Actions */}
      <div className="card" style={{ marginBottom: "1rem", padding: "0.75rem 1rem", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem" }}>
        <div style={{ display: "flex", gap: "0.25rem", alignItems: "center", fontSize: "0.85rem" }}>
          <button onClick={() => navigateUp(-1)} style={{ background: "none", border: "none", cursor: "pointer", fontWeight: 600, color: "var(--primary)", fontFamily: "var(--font-sans)" }}>Root</button>
          {folderPath.map((f, i) => (
            <span key={f.id}>
              <span style={{ color: "var(--gray-400)", margin: "0 0.25rem" }}>/</span>
              <button onClick={() => navigateUp(i)} style={{ background: "none", border: "none", cursor: "pointer", fontWeight: 500, color: "var(--primary)", fontFamily: "var(--font-sans)" }}>{f.name}</button>
            </span>
          ))}
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button className="btn btn-sm" onClick={() => setShowNewFolder(true)}>New Folder</button>
          <label className="btn btn-primary btn-sm" style={{ cursor: "pointer" }}>
            Upload File <input type="file" onChange={handleUpload} style={{ display: "none" }} />
          </label>
        </div>
      </div>

      {showNewFolder && (
        <div className="card" style={{ marginBottom: "1rem", padding: "0.75rem 1rem" }}>
          <form onSubmit={handleCreateFolder} style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <input value={folderName} onChange={e => setFolderName(e.target.value)} placeholder="Folder name" required autoFocus style={{ flex: 1, padding: "0.4rem 0.6rem", border: "1px solid var(--gray-300)", borderRadius: "var(--radius)", fontSize: "0.85rem" }} />
            <button type="submit" className="btn btn-primary btn-sm">Create</button>
            <button type="button" className="btn btn-sm" onClick={() => setShowNewFolder(false)}>Cancel</button>
          </form>
        </div>
      )}

      {/* Folders */}
      {folders.length > 0 && (
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "1rem" }}>
          {folders.map((f: any) => (
            <div key={f.id} onClick={() => navigateToFolder(f.id, f.name)} style={{ cursor: "pointer", padding: "0.75rem 1rem", background: "white", border: "1px solid var(--gray-200)", borderRadius: "var(--radius-lg)", display: "flex", alignItems: "center", gap: "0.5rem", transition: "all 0.15s", minWidth: 180 }} className="project-card">
              <span style={{ fontSize: "1.3rem" }}>&#128193;</span>
              <div>
                <div style={{ fontWeight: 600, fontSize: "0.85rem" }}>{f.name}</div>
                <div style={{ fontSize: "0.72rem", color: "var(--gray-500)" }}>{f.doc_count} docs, {f.subfolder_count} folders</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Documents */}
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
                      <a href={`${API_URL}/api/dms/documents/${d.id}/download`} className="btn btn-sm btn-primary" style={{ textDecoration: "none", fontSize: "0.72rem" }} target="_blank">Download</a>
                      <button className="btn btn-sm" onClick={() => setVersionDocId(versionDocId === d.id ? null : d.id)}>Versions</button>
                      <button className="btn btn-sm" onClick={async () => { try { await checkoutDoc({ id: d.id, body: {} }).unwrap(); alert("Checked out"); rLocks(); } catch (err: any) { alert(err?.data?.detail || "Failed"); } }}>Checkout</button>
                      <button className="btn btn-sm" onClick={async () => { await checkinDoc(d.id); alert("Checked in"); rLocks(); }}>Check-in</button>
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

      {/* Version history */}
      {versionDocId && versions.length > 0 && (
        <div className="card" style={{ marginTop: "1rem" }}>
          <h3 style={{ marginBottom: "0.75rem" }}>Version History</h3>
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
                  <td><a href={`${API_URL}/api/dms/documents/${versionDocId}/download?version=${v.version}`} className="btn btn-sm" style={{ textDecoration: "none", fontSize: "0.72rem" }} target="_blank">Download</a></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      </>}
    </div>
  );
}
