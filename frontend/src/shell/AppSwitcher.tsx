import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { APPS, AppDef } from "./navConfig";
import { Icon } from "./icons";

export default function AppSwitcher({ currentApp }: { currentApp: AppDef }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  return (
    <div className="app-switcher" ref={ref}>
      <button
        className="app-switcher-trigger"
        onClick={() => setOpen((o) => !o)}
        aria-label="Switch app"
        aria-expanded={open}
      >
        <span className="app-switcher-waffle">
          <Icon.AppGrid size={18} aria-hidden />
        </span>
      </button>

      {open && (
        <div className="app-switcher-panel" role="menu">
          <div className="app-switcher-panel-head">Apps</div>
          <div className="app-switcher-grid">
            {APPS.map((app) => (
              <button
                key={app.id}
                className={`app-tile ${app.id === currentApp.id ? "active" : ""}`}
                onClick={() => { navigate(app.path); setOpen(false); }}
                role="menuitem"
              >
                <span className="app-tile-icon" style={{ background: app.color }}>
                  {app.short}
                </span>
                <span className="app-tile-text">
                  <span className="app-tile-label">{app.label}</span>
                  <span className="app-tile-desc">{app.description}</span>
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
