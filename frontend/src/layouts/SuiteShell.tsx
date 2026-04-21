import { Outlet, useLocation } from "react-router-dom";
import SuiteBar from "../shell/SuiteBar";
import { useProjectWebSocket } from "../services/useWebSocket";

function ShellWsBridge() {
  const { pathname } = useLocation();
  const m = pathname.match(/^\/projects\/([^/]+)/);
  useProjectWebSocket(m?.[1]);
  return null;
}

export default function SuiteShell() {
  return (
    <div className="suite-shell">
      <ShellWsBridge />
      <SuiteBar />
      <div className="suite-body">
        <Outlet />
      </div>
    </div>
  );
}
