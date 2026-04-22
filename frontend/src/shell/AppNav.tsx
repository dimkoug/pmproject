import { NavLink } from "react-router-dom";
import { AppDef, NavGroup } from "./navConfig";
import { useRecentPages } from "./useRecentPages";

type Props = {
  app: AppDef;
  groups?: NavGroup[];
  basePath?: string;
  title?: string;
  subtitle?: string;
  topSlot?: React.ReactNode;
};

export default function AppNav({ app, groups, basePath, title, subtitle, topSlot }: Props) {
  const resolvedGroups = groups ?? app.groups;
  const recent = useRecentPages();

  const buildTo = (to: string) => {
    if (!basePath) return to;
    if (!to) return basePath;
    if (to.startsWith("/")) return to;
    return `${basePath.replace(/\/$/, "")}/${to}`;
  };

  return (
    <aside className="app-nav" style={{ "--app-color": app.color, "--app-accent": app.accent } as React.CSSProperties}>
      <div className="app-nav-head">
        <span className="app-nav-badge" style={{ background: app.color }}>{app.short}</span>
        <div className="app-nav-title-wrap">
          <span className="app-nav-title">{title ?? app.label}</span>
          {subtitle && <span className="app-nav-subtitle">{subtitle}</span>}
        </div>
      </div>
      {topSlot && <div className="app-nav-top-slot">{topSlot}</div>}
      <nav className="app-nav-list">
        {resolvedGroups.map((group, gi) => (
          <div className="app-nav-group" key={gi}>
            {group.title && <div className="app-nav-group-title">{group.title}</div>}
            {group.items.map((item) => (
              <NavLink
                key={item.to || "index"}
                to={buildTo(item.to)}
                end={item.end ?? item.to === ""}
                className={({ isActive }) => `app-nav-item ${isActive ? "active" : ""}`}
              >
                {item.label}
              </NavLink>
            ))}
          </div>
        ))}
        {recent.length > 1 && (
          <div className="app-nav-group app-nav-group-recent">
            <div className="app-nav-group-title">Recent</div>
            {recent.slice(1).map((r) => (
              <NavLink
                key={r.to}
                to={r.to}
                end
                className={({ isActive }) => `app-nav-item app-nav-item-recent ${isActive ? "active" : ""}`}
                title={r.to}
              >
                {r.label}
              </NavLink>
            ))}
          </div>
        )}
      </nav>
    </aside>
  );
}
