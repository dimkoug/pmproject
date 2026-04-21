import { Outlet, useLocation } from "react-router-dom";
import AppNav from "../shell/AppNav";
import { getAppByPath } from "../shell/navConfig";

export default function AppLayout() {
  const { pathname } = useLocation();
  const app = getAppByPath(pathname);

  return (
    <div className="app-shell">
      <AppNav app={app} />
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
