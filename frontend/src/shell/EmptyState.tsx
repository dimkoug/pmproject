import type { ReactNode } from "react";
import { Icon } from "./icons";
import type { IconName } from "./icons";

export type EmptyStateProps = {
  title: string;
  description?: string;
  icon?: IconName;
  cta?: ReactNode;
  compact?: boolean;
};

export default function EmptyState({ title, description, icon = "Folder", cta, compact = false }: EmptyStateProps) {
  const IconComp = Icon[icon];
  return (
    <div className={`empty-state ${compact ? "compact" : ""}`} role="status">
      <div className="empty-state-icon" aria-hidden>
        <IconComp size={compact ? 22 : 32} strokeWidth={1.5} />
      </div>
      <div className="empty-state-title">{title}</div>
      {description && <div className="empty-state-desc">{description}</div>}
      {cta && <div className="empty-state-cta">{cta}</div>}
    </div>
  );
}
