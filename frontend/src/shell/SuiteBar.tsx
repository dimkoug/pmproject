import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAppDispatch, useAppSelector } from "../app/hooks";
import { logout, patchUser } from "../services/authSlice";
import {
  useSearchQuery, useGetNotificationsQuery, useGetUnreadCountQuery,
  useMarkNotificationReadMutation, useMarkAllReadMutation,
  useUpdateMeSettingsMutation, useGetMyWorkspacesQuery, apiSlice,
} from "../services/api";
import AppSwitcher from "./AppSwitcher";
import { getAppByPath } from "./navConfig";
import { Icon } from "./icons";
import { useHotkeys } from "./useHotkeys";
import ShortcutsCheatsheet from "./ShortcutsCheatsheet";
import { SUPPORTED_LANGUAGES, setLanguage } from "../i18n";
import { COMMON_TIMEZONES } from "../i18n/format";
import { useFormat } from "../i18n/format";

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
  const { t, i18n } = useTranslation();
  const { formatDateTime } = useFormat();
  const [updateSettings] = useUpdateMeSettingsMutation();
  const { data: workspaces = [] } = useGetMyWorkspacesQuery();
  const activeWorkspace = (workspaces as any[]).find((w) => w.active);
  const switchWorkspace = (id: string) => {
    localStorage.setItem("activeWorkspaceId", id);
    // Drop all RTK Query caches so every list re-fetches with the new workspace scope.
    dispatch(apiSlice.util.resetApiState());
  };

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
    if (user?.language && user.language !== i18n.language) {
      void i18n.changeLanguage(user.language);
    }
  }, [user?.language, i18n]);

  const changeLanguage = async (code: string) => {
    setLanguage(code);
    if (user) {
      const r: any = await updateSettings({ language: code });
      if (!r.error) dispatch(patchUser({ language: code }));
    }
  };

  const changeTimezone = async (tz: string) => {
    if (!user) return;
    const r: any = await updateSettings({ timezone: tz });
    if (!r.error) dispatch(patchUser({ timezone: tz }));
  };

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
            placeholder={`${projectId ? t("shell.searchThisProject") : t("shell.searchEverywhere")}  (Ctrl+K)`}
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
        <span className={`suite-ws ${wsConnected ? "on" : "off"}`} title={wsConnected ? t("shell.live") : "Reconnecting…"}>
          <span className="suite-ws-dot" />
          <span className="suite-ws-label">{wsConnected ? t("shell.live") : t("shell.offline")}</span>
        </span>
        <div className="suite-notif" ref={notifRef}>
          <button
            className="suite-icon-btn"
            title={t("shell.notifications")}
            aria-label={`${t("shell.notifications")} (${unreadCount} unread)`}
            onClick={() => setNotifOpen((x) => !x)}
          >
            <Icon.Bell aria-hidden />
            {unreadCount > 0 && <span className="suite-notif-badge">{unreadCount > 99 ? "99+" : unreadCount}</span>}
          </button>
          {notifOpen && (
            <div className="suite-notif-panel" role="menu">
              <div className="suite-notif-head">
                <span>{t("shell.notifications")}</span>
                {notifications.some((n: any) => !n.is_read) && (
                  <button
                    className="btn btn-sm"
                    onClick={async () => { await markAll(); refetchCount(); refetchNotifs(); }}
                  >{t("shell.markAllRead")}</button>
                )}
              </div>
              {notifications.length === 0 ? (
                <div className="suite-notif-empty">{t("shell.noNotifications")}</div>
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
                        <div className="suite-notif-time">{formatDateTime(n.created_at)}</div>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
        <button className="suite-icon-btn" title={darkMode ? t("shell.lightMode") : t("shell.darkMode")} onClick={() => setDarkMode(!darkMode)}>
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
              {(workspaces as any[]).length > 1 && (
                <div className="suite-user-section">
                  <div className="suite-user-section-label">Workspace{activeWorkspace ? ` · ${activeWorkspace.name}` : ""}</div>
                  <select
                    className="suite-user-select"
                    value={activeWorkspace?.id || ""}
                    onChange={(e) => switchWorkspace(e.target.value)}
                  >
                    {(workspaces as any[]).map((w) => (
                      <option key={w.id} value={w.id}>{w.name}</option>
                    ))}
                  </select>
                </div>
              )}
              <button className="suite-user-item" onClick={() => { setUserOpen(false); navigate("/admin"); }}>{t("shell.workspaceSettings")}</button>
              <button className="suite-user-item" onClick={() => { setUserOpen(false); setCheatsheetOpen(true); }}>{t("shell.keyboardShortcuts")}</button>
              <div className="suite-user-section">
                <div className="suite-user-section-label">{t("shell.density")}</div>
                <div className="suite-density-toggle" role="radiogroup" aria-label="Row density">
                  <button
                    type="button"
                    role="radio"
                    aria-checked={density === "comfortable"}
                    className={`suite-density-opt ${density === "comfortable" ? "active" : ""}`}
                    onClick={() => setDensity("comfortable")}
                  >
                    {t("shell.densityComfortable")}
                  </button>
                  <button
                    type="button"
                    role="radio"
                    aria-checked={density === "compact"}
                    className={`suite-density-opt ${density === "compact" ? "active" : ""}`}
                    onClick={() => setDensity("compact")}
                  >
                    {t("shell.densityCompact")}
                  </button>
                </div>
              </div>
              <div className="suite-user-section">
                <div className="suite-user-section-label">{t("shell.language")}</div>
                <select
                  className="suite-user-select"
                  value={user?.language || i18n.language}
                  onChange={(e) => void changeLanguage(e.target.value)}
                >
                  {SUPPORTED_LANGUAGES.map((l) => (
                    <option key={l.code} value={l.code}>{l.label}</option>
                  ))}
                </select>
              </div>
              <div className="suite-user-section">
                <div className="suite-user-section-label">{t("shell.timezone")}</div>
                <select
                  className="suite-user-select"
                  value={user?.timezone || "UTC"}
                  onChange={(e) => void changeTimezone(e.target.value)}
                >
                  {COMMON_TIMEZONES.map((tz) => (
                    <option key={tz} value={tz}>{tz}</option>
                  ))}
                </select>
              </div>
              <div className="suite-user-section">
                <div className="suite-user-section-label">Notifications</div>
                <div style={{ display: "flex", flexDirection: "column", gap: "0.3rem" }}>
                  <label style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem", fontSize: "0.78rem" }}>
                    <input
                      type="checkbox"
                      checked={user?.notify_email ?? true}
                      onChange={async (e) => {
                        const v = e.target.checked;
                        const r: any = await updateSettings({ notify_email: v });
                        if (!r.error) dispatch(patchUser({ notify_email: v }));
                      }}
                    />
                    Email
                  </label>
                  <label style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem", fontSize: "0.78rem" }}>
                    <input
                      type="checkbox"
                      checked={user?.notify_sms ?? false}
                      onChange={async (e) => {
                        const v = e.target.checked;
                        const r: any = await updateSettings({ notify_sms: v });
                        if (!r.error) dispatch(patchUser({ notify_sms: v }));
                      }}
                    />
                    SMS
                  </label>
                  <input
                    type="tel"
                    className="suite-user-select"
                    placeholder="Phone (E.164, e.g. +14155551234)"
                    defaultValue={user?.phone || ""}
                    onBlur={async (e) => {
                      const v = e.target.value.trim();
                      if (v === (user?.phone || "")) return;
                      const r: any = await updateSettings({ phone: v || null });
                      if (!r.error) dispatch(patchUser({ phone: v || null }));
                    }}
                  />
                </div>
              </div>
              <button
                className="suite-user-item"
                onClick={async () => {
                  setUserOpen(false);
                  const token = localStorage.getItem("token");
                  if (!token) return;
                  try {
                    const r = await fetch(`${import.meta.env.VITE_API_URL || ""}/api/gdpr/export`, {
                      headers: { Authorization: `Bearer ${token}` },
                    });
                    if (!r.ok) throw new Error(`HTTP ${r.status}`);
                    const blob = await r.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = `gdpr-export-${(user?.id || "me").slice(0, 8)}.zip`;
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                    URL.revokeObjectURL(url);
                  } catch (e: any) {
                    alert(`Export failed: ${e?.message || e}`);
                  }
                }}
              >
                Download my data
              </button>
              <button
                className="suite-user-item danger"
                onClick={async () => {
                  setUserOpen(false);
                  const sure = window.confirm(
                    "Permanently delete your account?\n\nYour login will be removed and your name + email anonymized. Audit history is preserved.\n\nThis cannot be undone.",
                  );
                  if (!sure) return;
                  const token = localStorage.getItem("token");
                  try {
                    const r = await fetch(`${import.meta.env.VITE_API_URL || ""}/api/gdpr/me?confirm=true`, {
                      method: "DELETE",
                      headers: { Authorization: `Bearer ${token}` },
                    });
                    if (!r.ok) throw new Error(`HTTP ${r.status}`);
                    handleLogout();
                  } catch (e: any) {
                    alert(`Delete failed: ${e?.message || e}`);
                  }
                }}
              >
                Delete my account…
              </button>
              <button className="suite-user-item danger" onClick={handleLogout}>{t("common.signOut")}</button>
            </div>
          )}
        </div>
      </div>
      <ShortcutsCheatsheet open={cheatsheetOpen} onClose={() => setCheatsheetOpen(false)} />
    </header>
  );
}
