import { useState } from "react";
import {
  useGetCommentsQuery,
  useCreateCommentMutation,
} from "../services/api";
import { Icon } from "./icons";
import { SkeletonLine } from "./Skeleton";
import EmptyState from "./EmptyState";
import { useFormat } from "../i18n/format";

export function CommentsTab({
  targetType,
  targetId,
}: {
  targetType: string;
  targetId: string;
}) {
  const { data: comments = [], isLoading, refetch } = useGetCommentsQuery({ targetType, targetId });
  const [createComment, { isLoading: posting }] = useCreateCommentMutation();
  const [draft, setDraft] = useState("");
  const { formatDateTime } = useFormat();

  const submit = async () => {
    const body = draft.trim();
    if (!body) return;
    await createComment({ target_type: targetType, target_id: targetId, body });
    setDraft("");
    refetch();
  };

  if (isLoading) {
    return (
      <div>
        {[0, 1, 2].map((i) => (
          <div key={i} style={{ marginBottom: "0.75rem" }}>
            <SkeletonLine width="30%" height={10} style={{ marginBottom: "0.3rem" }} />
            <SkeletonLine width="100%" height={14} />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="drawer-comments">
      {comments.length === 0 ? (
        <EmptyState
          compact
          icon="Comment"
          title="No comments yet"
          description="Start the conversation for this record."
        />
      ) : (
        <ul className="drawer-comments-list">
          {comments.map((c: any) => (
            <li key={c.id} className="drawer-comment">
              <div className="drawer-comment-meta">
                <strong>{c.author_name || "Someone"}</strong>
                <span>{formatDateTime(c.created_at)}</span>
              </div>
              <div className="drawer-comment-body">{c.body}</div>
            </li>
          ))}
        </ul>
      )}
      <div className="drawer-comment-form">
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          rows={3}
          placeholder="Add a comment…"
        />
        <div className="drawer-comment-actions">
          <button
            type="button"
            className="btn btn-sm btn-primary"
            onClick={submit}
            disabled={posting || !draft.trim()}
          >
            <Icon.Comment size={14} /> Post
          </button>
        </div>
      </div>
    </div>
  );
}

export function ActivityTab({
  items,
  isLoading,
}: {
  items: { id?: string; kind?: string; label?: string; at?: string; actor?: string }[];
  isLoading?: boolean;
}) {
  const { formatDateTime } = useFormat();
  if (isLoading) {
    return (
      <div>
        {[0, 1, 2, 3].map((i) => (
          <div key={i} style={{ display: "flex", gap: "0.5rem", marginBottom: "0.6rem" }}>
            <SkeletonLine width={8} height={8} style={{ borderRadius: 999, marginTop: 6, flex: "0 0 auto" }} />
            <div style={{ flex: 1 }}>
              <SkeletonLine width="70%" height={12} style={{ marginBottom: "0.2rem" }} />
              <SkeletonLine width="40%" height={10} />
            </div>
          </div>
        ))}
      </div>
    );
  }
  if (!items || items.length === 0) {
    return (
      <EmptyState
        compact
        icon="Activity"
        title="No recent activity"
        description="Changes will show up here."
      />
    );
  }
  return (
    <ol className="drawer-activity-list">
      {items.map((it, i) => (
        <li key={it.id ?? i} className="drawer-activity-item">
          <span className="drawer-activity-dot" aria-hidden />
          <div>
            <div className="drawer-activity-label">{it.label ?? it.kind ?? "Event"}</div>
            <div className="drawer-activity-meta">
              {it.actor ? `${it.actor} · ` : ""}
              {it.at ? formatDateTime(it.at) : ""}
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}

export function OverviewGrid({ rows }: { rows: { label: string; value: React.ReactNode }[] }) {
  return (
    <dl className="drawer-overview-grid">
      {rows.map((r, i) => (
        <div key={i} className="drawer-overview-row">
          <dt>{r.label}</dt>
          <dd>{r.value ?? <span style={{ color: "var(--gray-400)" }}>—</span>}</dd>
        </div>
      ))}
    </dl>
  );
}
