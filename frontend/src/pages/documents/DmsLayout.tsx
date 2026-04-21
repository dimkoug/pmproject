import { Outlet } from "react-router-dom";
import { useGetDmsDashboardQuery } from "../../services/api";
import { useProjectContext } from "../../shell/useProjectContext";

export default function DmsLayout() {
  const projectId = useProjectContext();
  const { data: dash } = useGetDmsDashboardQuery(projectId);

  return (
    <div>
      {dash && (
        <div className="stats-grid" style={{ marginBottom: "1.25rem" }}>
          <div className="stat-card"><div className="label">Documents</div><div className="value">{dash.documents}</div></div>
          <div className="stat-card"><div className="label">Folders</div><div className="value">{dash.folders}</div></div>
          <div className="stat-card"><div className="label">Versions</div><div className="value">{dash.versions}</div></div>
          <div className="stat-card"><div className="label">Total Size</div><div className="value">{dash.total_size_mb} MB</div></div>
        </div>
      )}
      <Outlet />
    </div>
  );
}
