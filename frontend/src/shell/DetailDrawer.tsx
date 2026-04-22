import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { Icon } from "./icons";
import TagPicker from "./TagPicker";

export type DrawerTabKey = "overview" | "activity" | "comments" | "attachments" | "history";

export type DrawerContext = {
  entity: string;
  id: string;
  close: () => void;
};

export type DrawerTabRenderer = (ctx: DrawerContext) => ReactNode;

export type DrawerBody = {
  title: (ctx: DrawerContext) => ReactNode;
  statusBadges?: (ctx: DrawerContext) => ReactNode;
  tabs: Partial<Record<DrawerTabKey, DrawerTabRenderer>>;
  defaultTab?: DrawerTabKey;
};

type Registry = Map<string, DrawerBody>;

const registry: Registry = new Map();

export function registerDrawerBody(entity: string, body: DrawerBody) {
  registry.set(entity, body);
}

export function parsePeekParam(v: string | null): { entity: string; id: string } | null {
  if (!v) return null;
  const idx = v.indexOf(":");
  if (idx <= 0) return null;
  const entity = v.slice(0, idx).trim();
  const id = v.slice(idx + 1).trim();
  if (!entity || !id) return null;
  return { entity, id };
}

export function buildPeekParam(entity: string, id: string | number) {
  return `${entity}:${id}`;
}

export function useDrawerPeek() {
  const [searchParams, setSearchParams] = useSearchParams();
  const open = useCallback(
    (entity: string, id: string | number) => {
      const next = new URLSearchParams(searchParams);
      next.set("peek", buildPeekParam(entity, id));
      setSearchParams(next, { replace: false });
    },
    [searchParams, setSearchParams],
  );
  const close = useCallback(() => {
    const next = new URLSearchParams(searchParams);
    next.delete("peek");
    setSearchParams(next, { replace: true });
  }, [searchParams, setSearchParams]);
  return { open, close };
}

const TAB_ORDER: { key: DrawerTabKey; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "activity", label: "Activity" },
  { key: "comments", label: "Comments" },
  { key: "attachments", label: "Attachments" },
  { key: "history", label: "History" },
];

export default function DetailDrawer() {
  const [searchParams, setSearchParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const peekRaw = searchParams.get("peek");
  const parsed = useMemo(() => parsePeekParam(peekRaw), [peekRaw]);
  const body = parsed ? registry.get(parsed.entity) : null;

  const [activeTab, setActiveTab] = useState<DrawerTabKey>("overview");
  const panelRef = useRef<HTMLDivElement>(null);

  const close = useCallback(() => {
    const next = new URLSearchParams(searchParams);
    next.delete("peek");
    setSearchParams(next, { replace: true });
  }, [searchParams, setSearchParams]);

  useEffect(() => {
    if (!parsed) return;
    if (body?.defaultTab) {
      setActiveTab(body.defaultTab);
    } else {
      const firstAvailable = TAB_ORDER.find((t) => body?.tabs?.[t.key])?.key ?? "overview";
      setActiveTab(firstAvailable);
    }
  }, [parsed?.entity, parsed?.id, body]);

  useEffect(() => {
    if (!parsed) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        close();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [parsed, close]);

  if (!parsed || !body) return null;

  const ctx: DrawerContext = { entity: parsed.entity, id: parsed.id, close };
  const availableTabs = TAB_ORDER.filter((t) => body.tabs[t.key]);
  const renderer = body.tabs[activeTab];

  void location;
  void navigate;

  return (
    <div className="detail-drawer-root" role="dialog" aria-modal="true" aria-label="Detail drawer">
      <div className="detail-drawer-backdrop" onClick={close} />
      <aside className="detail-drawer-panel" ref={panelRef}>
        <header className="detail-drawer-head">
          <div className="detail-drawer-title-wrap">
            <div className="detail-drawer-title">{body.title(ctx)}</div>
            {body.statusBadges && (
              <div className="detail-drawer-badges">{body.statusBadges(ctx)}</div>
            )}
          </div>
          <button
            type="button"
            className="detail-drawer-close"
            onClick={close}
            aria-label="Close detail drawer"
          >
            <Icon.Close size={16} />
          </button>
        </header>
        <div className="detail-drawer-tags">
          <TagPicker entityType={parsed.entity} entityId={parsed.id} compact />
        </div>
        {availableTabs.length > 1 && (
          <div className="detail-drawer-tabs" role="tablist">
            {availableTabs.map((t) => (
              <button
                key={t.key}
                type="button"
                role="tab"
                aria-selected={activeTab === t.key}
                className={`detail-drawer-tab ${activeTab === t.key ? "active" : ""}`}
                onClick={() => setActiveTab(t.key)}
              >
                {t.label}
              </button>
            ))}
          </div>
        )}
        <div className="detail-drawer-body" role="tabpanel">
          {renderer ? renderer(ctx) : <div className="detail-drawer-empty">No content for this tab.</div>}
        </div>
      </aside>
    </div>
  );
}
