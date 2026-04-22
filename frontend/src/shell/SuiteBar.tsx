import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAppDispatch, useAppSelector } from "../app/hooks";
import { logout } from "../services/authSlice";
import {
  useSearchQuery, useGetNotificationsQuery, useGetUnreadCountQuery,
  useMarkNotificationReadMutation, useMarkAllReadMutation,
} from "../services/api";
import AppSwitcher from "./AppSwitcher";
import { getAppByPath } from "./navConfig";
import { Icon } from "./icons";
import { useHotkeys } from "./useHotkeys";
import ShortcutsCheatsheet from "./ShortcutsCheatsheet";

export default function SuiteBar() {
  const location = useLocation();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const user = useAppSelector((s) => s.auth.user);
  const wsConnected = useAppSelector((s) => s.ws.connected);
  const [userOpen, setUserOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [darkMode, setDarkMode] = useState(localStorage.getItem("dark") === "1");
  const [density, setDensity] = useState<"comfortable" | "compact">(
    (localStorage.getItem("density") as "comfortable" | "compact") || "comfortable",
  );
  const [searchQ, setSearchQ] = useState("");
  const [searchFocus, setSearchFocus] = useState(false);
  const [cheatsheetOpen, setCheatsheetOpen] = useState(false);
  const userRef = useRef<HTMLDivElement>(null);
  const notifRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  useHotkeys([
    {
      combo: "ctrl+k",
      allowInInputs: true,
      handler: (e) => {
        e.preventDefault();
        searchInputRef.current?.focus();
      },
    },
    {
      combo: "/",
      handler: (e) => {
        e.preventDefault();
        searchInputRef.current?.focus();
      },
    },
    {
      combo: "shift+?",
      handler: (e) => {
        e.preventDefault();
        setCheatsheetOpen(true);
      },
    },
  ]);

  const { data: unreadData, refetch: refetchCount } = useGetUnreadCountQuery(undefined, { pollingInterval: 30_000 });
  const { data: notifications = [], refetch: refetchNotifs } = useGetNotificationsQuery(undefined, { skip: !notifOpen });
  const [markOneRead] = useMarkNotificationReadMutation();
  const [markAll] = useMarkAllReadMutation();
  const unreadCount: number = unreadData?.unread ?? 0;

  const currentApp = getAppByPath(location.pathname);
  const projectMatch = location.pathname.match(/^\/projects\/([^/]+)/);
  const projectId = projectMatch?.[1];
  const { data: searchResults = [] } = useSearchQuery(
    { q: searchQ, projectId },
    { skip: searchQ.length < 2 }
  );

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", darkMode ? "dark" : "light");
    localStorage.setItem("dark", darkMode ? "1" : "0");
  }, [darkMode]);

  useEffect(() => {
    document.documentElement.setAttribute("data-density", density);
    localStorage.setItem("density", density);
  }, [density]);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (userRef.current && !userRef.current.contains(e.target as Node)) setUserOpen(false);
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) setNotifOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const handleLogout = () => {
    dispatch(logout());
    navigate("/login");
  };

  const initials = (user?.name || user?.email || "?")
    .split(/\s+/)
    .map((s) => s[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  const openSearchResult = (r: any) => {
    setSearchQ("");
    setSearchFocus(false);
    if (r.project_id) navigate(`/projects/${r.project_id}/tasks`);
  };

  return (
    <header className="suite-bar">
      <div className="suite-bar-left">
        <AppSwitcher currentApp={currentApp} />
        <div className="suite-brand">
          <span className="suite-brand-dot" style={{ background: currentApp.color }} />
          <span className="suite-brand-name">Acme</span>
          <span className="suite-brand-sep">/</span>
          <span className="suite-brand-app">{currentApp.label}</span>
        </div>
      </div>

      <div className="suite-bar-center">
        <div className={`suite-search ${searchFocus ? "focused" : ""}`}>
          <Icon.Search size={14} aria-hidden />
          <input
            ref={searchInputRef}
            value={searchQ}
            onChange={(e) => setSearchQ(e.target.value)}
            onFocus={() => setSearchFocus(true)}
            onBlur={() => setTimeout(() => setSearchFocus(false), 150)}
            placeholder={`Search${projectId ? " this project" : " everywhere"}…  (Ctrl+K)`}
          />
          {searchFocus && searchQ.length >= 2 && searchResults.length > 0 && (
            <div className="suite-search-panel">
              {searchResults.map((r: any, i: number) => (
                <button key={i} className="suite-search-item" onMouseDown={() => openSearchResult(r)}>
                  <span className="suite-search-kind">{r.type}</span>
                  <span className="suite-search-title">{r.title}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="suite-bar-right">
        <span className={`suite-ws ${wsConnected ? "on" : "off"}`} title={wsConnected ? "Live" : "Reconnecting…"}>
          <span className="suite-ws-dot" />
          <span className="suite-ws-label">{wsConnected ? "Live" : "Offline"}</span>
        </span>
        <div className="suite-notif" ref={notifRef}>
          <button
            className="suite-icon-btn"
            title="Notifications"
            aria-label={`Notifications (${unreadCount} unread)`}
            onClick={() => setNotifOpen((x) => !x)}
          >
            <Icon.Bell aria-hidden />
            {unreadCount > 0 && <span className="suite-notif-badge">{unreadCount > 99 ? "99+" : unreadCount}</span>}
          </button>
          {notifOpen && (
            <div className="suite-notif-panel" role="menu">
              <div className="suite-notif-head">
                <span>Notifications</span>
                {notifications.some((n: any) => !n.is_read) && (
                  <button
                    className="btn btn-sm"
                    onClick={async () => { await markAll(); refetchCount(); refetchNotifs(); }}
                  >Mark all read</button>
                )}
              </div>
              {notifications.length === 0 ? (
                <div className="suite-notif-empty">You're all caught up.</div>
              ) : (
                <div className="suite-notif-list">
                  {notifications.map((n: any) => (
                    <button
                      key={n.id}
                      className={`suite-notif-item ${n.is_read ? "read" : "unread"}`}
                      onClick={async () => {
                        if (!n.is_read) { await markOneRead(n.id); refetchCount(); }
                        if (n.link) { navigate(n.link); setNotifOpen(false); }
                      }}
                    >
                      {!n.is_read && <span className="suite-notif-dot" aria-hidden />}
                      <div className="suite-notif-body">
                        <div className="suite-notif-title">{n.title}</div>
                        {n.body && <div className="suite-notif-snippet">{n.body}</div>}
                        <div className="suite-notif-time">{new Date(n.created_at).toLocaleString()}</div>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
        <button className="suite-icon-btn" title={darkMode ? "Light mode" : "Dark mode"} onClick={() => setDarkMode(!darkMode)}>
          {darkMode ? <Icon.Sun aria-hidden /> : <Icon.Moon aria-hidden />}
        </button>
        <div className="suite-user" ref={userRef}>
          <button className="suite-user-trigger" onClick={() => setUserOpen((o) => !o)} aria-expanded={userOpen}>
            <span className="suite-user-avatar">{initials}</span>
          </button>
          {userOpen && (
            <div className="suite-user-panel" role="menu">
              <div className="suite-user-head">
                <span className="suite-user-avatar lg">{initials}</span>
                <div>
                  <div className="suite-user-name">{user?.name || "Account"}</div>
                  <div className="suite-user-email">{user?.email}</div>
                </div>
              </div>
              <button className="suite-user-item" onClick={() => { setUserOpen(false); navigate("/admin"); }}>Workspace settings</button>
              <button className="suite-user-item" onClick={() => { setUserOpen(false); setCheatsheetOpen(true); }}>Keyboard shortcuts</button>
              <div className="suite-user-section">
                <div className="suite-user-section-label">Density</div>
                <div className="suite-density-toggle" role="radiogroup" aria-label="Row density">
                  <button
                    type="button"
                    role="radio"
                    aria-checked={density === "comfortable"}
                    className={`suite-density-opt ${density === "comfortable" ? "active" : ""}`}
                    onClick={() => setDensity("comfortable")}
                  >
                    Comfortable
                  </button>
                  <button
                    type="button"
                    role="radio"
                    aria-checked={density === "compact"}
                    className={`suite-density-opt ${density === "compact" ? "active" : ""}`}
                    onClick={() => setDensity("compact")}
                  >
                    Compact
                  </button>
                </div>
              </div>
              <button className="suite-user-item danger" onClick={handleLogout}>Sign out</button>
            </div>
          )}
        </div>
      </div>
      <ShortcutsCheatsheet open={cheatsheetOpen} onClose={() => setCheatsheetOpen(false)} />
    </header>
  );
}
