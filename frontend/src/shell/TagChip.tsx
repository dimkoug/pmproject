import type { CSSProperties } from "react";
import { Icon } from "./icons";

export type TagChipData = {
  id: string;
  name: string;
  color?: string | null;
};

export type TagChipProps = {
  tag: TagChipData;
  onRemove?: () => void;
  onClick?: () => void;
  size?: "sm" | "md";
};

function hexToRgba(hex: string, alpha: number): string | null {
  const m = hex.trim().match(/^#?([0-9a-f]{3}|[0-9a-f]{6})$/i);
  if (!m) return null;
  let h = m[1];
  if (h.length === 3) h = h.split("").map((c) => c + c).join("");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export default function TagChip({ tag, onRemove, onClick, size = "sm" }: TagChipProps) {
  const color = tag.color || "#6b7280";
  const bg = hexToRgba(color, 0.14) || "rgba(107,114,128,0.14)";
  const border = hexToRgba(color, 0.28) || "rgba(107,114,128,0.28)";
  const style: CSSProperties = {
    background: bg,
    color,
    borderColor: border,
  };
  return (
    <span className={`tag-chip size-${size} ${onClick ? "clickable" : ""}`} style={style} onClick={onClick}>
      <span className="tag-chip-dot" style={{ background: color }} aria-hidden />
      <span className="tag-chip-label">{tag.name}</span>
      {onRemove && (
        <button
          type="button"
          className="tag-chip-remove"
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          aria-label={`Remove tag ${tag.name}`}
        >
          <Icon.Close size={10} />
        </button>
      )}
    </span>
  );
}
