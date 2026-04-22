import { useEffect, useMemo, useRef, useState } from "react";
import {
  useGetTagsQuery,
  useGetTagsForEntityQuery,
  useAttachTagMutation,
  useDetachTagMutation,
} from "../services/api";
import TagChip from "./TagChip";
import { Icon } from "./icons";

export type TagPickerProps = {
  entityType: string;
  entityId: string;
  readOnly?: boolean;
  compact?: boolean;
};

export default function TagPicker({ entityType, entityId, readOnly = false, compact = false }: TagPickerProps) {
  const { data: allTags = [] } = useGetTagsQuery();
  const { data: attached = [] } = useGetTagsForEntityQuery({ entityType, entityId });
  const [attachTag] = useAttachTagMutation();
  const [detachTag] = useDetachTagMutation();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
        setQuery("");
      }
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const attachedIds = useMemo(() => new Set((attached as any[]).map((t) => t.id)), [attached]);
  const available = useMemo(
    () =>
      (allTags as any[]).filter(
        (t) =>
          !attachedIds.has(t.id) &&
          (!query || t.name.toLowerCase().includes(query.toLowerCase())),
      ),
    [allTags, attachedIds, query],
  );

  return (
    <div className={`tag-picker ${compact ? "compact" : ""}`} ref={ref}>
      <div className="tag-picker-chips">
        {(attached as any[]).length === 0 && (
          <span className="tag-picker-empty">{readOnly ? "No tags" : "No tags yet"}</span>
        )}
        {(attached as any[]).map((t) => (
          <TagChip
            key={t.id}
            tag={t}
            size={compact ? "sm" : "md"}
            onRemove={
              readOnly
                ? undefined
                : async () => {
                    await detachTag({ tagId: t.id, entityType, entityId });
                  }
            }
          />
        ))}
        {!readOnly && (
          <button
            type="button"
            className="tag-picker-add"
            onClick={() => setOpen((o) => !o)}
            aria-label="Add tag"
          >
            <Icon.Plus size={12} /> tag
          </button>
        )}
      </div>
      {!readOnly && open && (
        <div className="tag-picker-panel" role="menu">
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search tags…"
            autoFocus
          />
          <div className="tag-picker-list">
            {available.length === 0 ? (
              <div className="tag-picker-list-empty">
                {query ? "No matching tags" : "All tags already attached"}
              </div>
            ) : (
              available.slice(0, 20).map((t) => (
                <button
                  key={t.id}
                  type="button"
                  className="tag-picker-item"
                  onClick={async () => {
                    await attachTag({ tagId: t.id, entityType, entityId });
                    setQuery("");
                    setOpen(false);
                  }}
                >
                  <TagChip tag={t} size="sm" />
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
