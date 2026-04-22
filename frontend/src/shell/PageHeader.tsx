import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { Icon } from "./icons";

export type Crumb = { to?: string; label: string };

type Props = {
  title: string;
  subtitle?: string;
  breadcrumbs?: Crumb[];
  actions?: ReactNode;
  meta?: ReactNode;
};

export default function PageHeader({ title, subtitle, breadcrumbs, actions, meta }: Props) {
  return (
    <header className="page-header-block">
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav className="page-breadcrumbs" aria-label="Breadcrumb">
          {breadcrumbs.map((c, i) => (
            <span key={i} className="page-breadcrumb">
              {c.to ? <Link to={c.to}>{c.label}</Link> : <span>{c.label}</span>}
              {i < breadcrumbs.length - 1 && (
                <span className="page-breadcrumb-sep" aria-hidden>
                  <Icon.ChevronRight size={12} />
                </span>
              )}
            </span>
          ))}
        </nav>
      )}
      <div className="page-header">
        <div>
          <h1 className="page-title">{title}</h1>
          {subtitle && <p className="page-subtitle">{subtitle}</p>}
          {meta && <div className="page-meta">{meta}</div>}
        </div>
        {actions && <div className="page-header-actions">{actions}</div>}
      </div>
    </header>
  );
}
