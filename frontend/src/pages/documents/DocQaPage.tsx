import { useState } from "react";
import {
  useDocQaMutation,
  useLazySemanticSearchQuery,
  useRebuildEmbeddingsMutation,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import { Icon } from "../../shell/icons";
import { notifyUser } from "../../shell/modalService";

export default function DocQaPage() {
  const [askQa, { isLoading: asking, data: qaData }] = useDocQaMutation();
  const [trigger, { data: hits = [], isFetching: searching }] = useLazySemanticSearchQuery();
  const [rebuild, { isLoading: rebuilding }] = useRebuildEmbeddingsMutation();
  const [mode, setMode] = useState<"search" | "qa">("qa");
  const [q, setQ] = useState("");

  const submit = async () => {
    if (!q.trim()) return;
    if (mode === "qa") {
      await askQa({ question: q.trim(), top_k: 5 });
    } else {
      await trigger({ q: q.trim(), topK: 15 });
    }
  };

  return (
    <div>
      <PageHeader
        title="Document Q&A"
        subtitle="Ask questions or run a semantic search across your indexed documents. Re-index when you upload new content."
      />
      <CommandBar
        items={[
          {
            key: "rebuild",
            label: rebuilding ? "Re-indexing…" : "Re-index all documents",
            onClick: async () => {
              const r: any = await rebuild();
              if (r.error) {
                await notifyUser({ title: "Re-index failed", description: (r.error as any)?.data?.detail });
                return;
              }
              await notifyUser({
                title: "Re-index complete",
                description: `Embedded ${r.data?.documents_embedded ?? 0} of ${r.data?.documents_total ?? 0} docs · ${r.data?.chunks_written ?? 0} chunks (${r.data?.embedding_source})`,
              });
            },
          },
        ]}
      />

      <div style={{ display: "inline-flex", gap: "0.25rem", marginBottom: "0.75rem" }}>
        <button className={`btn btn-sm ${mode === "qa" ? "btn-primary" : ""}`} onClick={() => setMode("qa")}>
          <Icon.Comment size={14} /> Ask a question
        </button>
        <button className={`btn btn-sm ${mode === "search" ? "btn-primary" : ""}`} onClick={() => setMode("search")}>
          <Icon.Search size={14} /> Semantic search
        </button>
      </div>

      <div className="card" style={{ display: "flex", gap: "0.5rem", alignItems: "stretch" }}>
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") submit(); }}
          placeholder={
            mode === "qa"
              ? "e.g. What's the SLA for invoice payment in our standard MSA?"
              : "e.g. SLA invoice payment terms"
          }
          style={{
            flex: 1,
            padding: "0.5rem 0.75rem",
            border: "1px solid var(--gray-200)",
            borderRadius: "var(--radius)",
            fontFamily: "var(--font-sans)",
            fontSize: "0.85rem",
          }}
        />
        <button className="btn btn-primary" onClick={submit} disabled={asking || searching || !q.trim()}>
          {asking || searching ? "Working…" : mode === "qa" ? "Ask" : "Search"}
        </button>
      </div>

      {mode === "qa" && qaData && (
        <div className="card">
          <div className="card-header" style={{ marginBottom: "0.5rem" }}>
            <h2 style={{ fontSize: "1rem" }}>Answer</h2>
            {qaData.answer_source && (
              <span className="badge badge-gray">source: {qaData.answer_source}</span>
            )}
          </div>
          <div style={{ whiteSpace: "pre-wrap", fontSize: "0.9rem", color: "var(--gray-800)", lineHeight: 1.5 }}>
            {qaData.answer || qaData.note || "No answer."}
          </div>
          {qaData.sources && qaData.sources.length > 0 && (
            <div style={{ marginTop: "1rem" }}>
              <div style={{ fontSize: "0.72rem", fontWeight: 600, color: "var(--gray-500)", textTransform: "uppercase", marginBottom: "0.4rem" }}>
                Sources
              </div>
              <ol style={{ margin: 0, paddingLeft: "1.25rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {qaData.sources.map((s: any, i: number) => (
                  <li key={s.chunk_id} style={{ fontSize: "0.82rem" }}>
                    <strong>[{i + 1}] {s.document_title}</strong>{" "}
                    <span style={{ color: "var(--gray-500)" }}>· score {s.score?.toFixed(3)}</span>
                    <div style={{ color: "var(--gray-700)", marginTop: "0.2rem" }}>{s.content}</div>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>
      )}

      {mode === "search" && hits && (hits as any[]).length > 0 && (
        <div className="card" style={{ padding: 0 }}>
          <table>
            <thead>
              <tr>
                <th style={{ width: "5ch" }}>#</th>
                <th>Document</th>
                <th>Passage</th>
                <th style={{ width: "8ch", textAlign: "right" }}>Score</th>
              </tr>
            </thead>
            <tbody>
              {(hits as any[]).map((h, i) => (
                <tr key={h.chunk_id}>
                  <td>{i + 1}</td>
                  <td style={{ fontWeight: 500 }}>{h.document_title}</td>
                  <td style={{ color: "var(--gray-700)" }}>{h.content}</td>
                  <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{h.score?.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {mode === "search" && !searching && (hits as any[]).length === 0 && q && (
        <div className="card" style={{ color: "var(--gray-500)" }}>
          No matches. If you've never run "Re-index all documents", do that first — chunks have to be embedded before they're searchable.
        </div>
      )}
    </div>
  );
}
