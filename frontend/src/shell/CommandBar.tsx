import { useMemo } from "react";
import type { ReactNode } from "react";
import { Icon } from "./icons";
import { useHotkeys } from "./useHotkeys";

export type CommandItem = {
  key: string;
  label: string;
  icon?: ReactNode;
  onClick?: () => void;
  to?: string;
  variant?: "default" | "primary" | "danger";
  disabled?: boolean;
  title?: string;
  hidden?: boolean;
};

type Props = {
  items: CommandItem[];
  overflow?: CommandItem[];
  right?: ReactNode;
};

const variantClass: Record<NonNullable<CommandItem["variant"]>, string> = {
  default: "",
  primary: "btn-primary",
  danger: "btn-danger",
};

export default function CommandBar({ items, overflow, right }: Props) {
  const visible = items.filter((i) => !i.hidden);
  const visibleOverflow = (overflow ?? []).filter((i) => !i.hidden);

  const primary = useMemo(
    () => visible.find((i) => i.variant === "primary" && i.onClick && !i.disabled),
    [visible],
  );
  useHotkeys(
    useMemo(
      () =>
        primary
          ? [
              {
                combo: "n",
                description: primary.label,
                handler: (e) => {
                  e.preventDefault();
                  primary.onClick?.();
                },
              },
            ]
          : [],
      [primary],
    ),
  );

  return (
    <div className="command-bar">
      <div className="command-bar-items">
        {visible.map((item) => (
          <CommandButton key={item.key} item={item} />
        ))}
        {visibleOverflow.length > 0 && (
          <details className="command-overflow">
            <summary className="btn btn-sm" aria-label="More actions">
              <Icon.More size={14} aria-hidden /> More
            </summary>
            <div className="command-overflow-panel">
              {visibleOverflow.map((item) => (
                <CommandButton key={item.key} item={item} overflow />
              ))}
            </div>
          </details>
        )}
      </div>
      {right && <div className="command-bar-right">{right}</div>}
    </div>
  );
}

function CommandButton({ item, overflow = false }: { item: CommandItem; overflow?: boolean }) {
  const cls = `btn btn-sm ${variantClass[item.variant ?? "default"]}${overflow ? " command-overflow-item" : ""}`;
  if (item.to) {
    return (
      <a href={item.to} className={cls} title={item.title} aria-disabled={item.disabled}>
        {item.icon && <span className="command-icon">{item.icon}</span>}
        {item.label}
      </a>
    );
  }
  return (
    <button
      type="button"
      className={cls}
      onClick={item.onClick}
      disabled={item.disabled}
      title={item.title}
    >
      {item.icon && <span className="command-icon">{item.icon}</span>}
      {item.label}
    </button>
  );
}
