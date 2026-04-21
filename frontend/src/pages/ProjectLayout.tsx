import { NavLink, Outlet, useParams } from "react-router-dom";
import { useGetProjectQuery } from "../services/api";
import AppNav from "../shell/AppNav";
import { APPS, NavGroup, PROJECT_NAV } from "../shell/navConfig";

export default function ProjectLayout() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: project } = useGetProjectQuery(projectId!);
  const projectsApp = APPS[0];

  const groups: NavGroup[] = [
    ...PROJECT_NAV,
    { title: "Related", items: [
      { to: `/sales?project=${projectId}`, label: "Opportunities" },
      { to: `/finance/invoices?project=${projectId}`, label: "Invoices" },
      { to: `/finance/purchase-orders?project=${projectId}`, label: "Purchase Orders" },
      { to: `/finance/budgets?project=${projectId}`, label: "Budgets" },
      { to: `/documents?project=${projectId}`, label: "Documents" },
    ]},
  ];

  return (
    <div className="app-shell">
      <AppNav
        app={projectsApp}
        groups={groups}
        basePath={`/projects/${projectId}`}
        title={project?.name || "Project"}
        subtitle={project?.development_approach}
        topSlot={
          <NavLink to="/" className="app-nav-back">
            <span aria-hidden>&larr;</span> All Projects
          </NavLink>
        }
      />
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
