import { useState } from "react";
import {
  useGetAnnotationsQuery, useCreateAnnotationMutation, useResolveAnnotationMutation,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import { promptForValues } from "../../shell/modalService";

export default function AnnotationsPage() {
  const [docId, setDocId] = useState<string | null>(null);
  const { data: annotations = [], refetch } = useGetAnnotationsQuery(docId!, { skip: !docId });
  const [createAnn] = useCreateAnnotationMutation();
  const [resolveAnn] = useResolveAnnotationMutation();

  return (
    <div>
      <PageHeader title="Annotations" subtitle="Threaded document comments — pick a document to view its annotations." />
      <CommandBar
        items={[
          {
            key: "comment", label: "Add comment", variant: "primary",
            disabled: !docId,
            onClick: async () => {
              if (!docId) return;
              const v = await promptForValues({
                title: "Add comment",
                submitLabel: "Add",
                fields: [
                  { name: "body", label: "Comment", kind: "textarea", required: true },
                ],
              });
              if (!v) return;
              await createAnn({ document_id: docId, body: v.body });
              refetch();
            },
          },
        ]}
        right={
          <input
            placeholder="Document ID"
            value={docId || ""}
            onChange={(e) => setDocId(e.target.value || null)}
            style={{ padding: "0.3rem 0.5rem", border: "1px solid var(--gray-300)", borderRadius: 4, fontSize: "0.82rem" }}
          />
        }
      />
      <div className="card" style={{ padding: 0 }}>
        {!docId && <div style={{ textAlign: "center", color: "var(--gray-500)", padding: "2rem" }}>Enter a document ID above to load its annotations.</div>}
        {docId && annotations.length === 0 && <div style={{ textAlign: "center", color: "var(--gray-500)", padding: "2rem" }}>No annotations on this document.</div>}
        {docId && annotations.map((a: any) => (
          <div key={a.id} style={{ padding: "0.5rem 1rem", borderTop: "1px solid var(--gray-100)", display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.5rem" }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: "0.85rem", fontWeight: a.resolved ? 400 : 500, textDecoration: a.resolved ? "line-through" : "none" }}>{a.body}</div>
              <div style={{ fontSize: "0.72rem", color: "var(--gray-500)" }}>{a.author_id?.slice(0, 8)}… · {a.created_at ? new Date(a.created_at).toLocaleString() : ""}</div>
            </div>
            {!a.resolved && (
              <button className="btn btn-sm" onClick={async () => { await resolveAnn(a.id); refetch(); }}>
                Resolve
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
