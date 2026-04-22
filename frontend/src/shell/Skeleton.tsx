import type { CSSProperties } from "react";

type LineProps = { width?: string | number; height?: string | number; className?: string; style?: CSSProperties };

function sizeValue(v?: string | number) {
  if (v === undefined) return undefined;
  return typeof v === "number" ? `${v}px` : v;
}

export function SkeletonLine({ width = "100%", height = 12, className, style }: LineProps) {
  return (
    <span
      className={`skeleton-line ${className ?? ""}`}
      style={{ width: sizeValue(width), height: sizeValue(height), ...style }}
      aria-hidden
    />
  );
}

export function SkeletonRow({ columns = 4 }: { columns?: number }) {
  return (
    <tr className="skeleton-row">
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i}>
          <SkeletonLine width={i === 0 ? "60%" : i === columns - 1 ? "40%" : "80%"} />
        </td>
      ))}
    </tr>
  );
}

type SkeletonCardProps = {
  lines?: number;
  heightPerLine?: number;
  showTitle?: boolean;
  className?: string;
};

export function SkeletonCard({
  lines = 3,
  heightPerLine = 12,
  showTitle = true,
  className,
}: SkeletonCardProps) {
  return (
    <div className={`card skeleton-card ${className ?? ""}`} aria-busy="true">
      {showTitle && <SkeletonLine width="42%" height={18} style={{ marginBottom: "0.75rem" }} />}
      {Array.from({ length: lines }).map((_, i) => (
        <SkeletonLine
          key={i}
          width={i === lines - 1 ? "55%" : "100%"}
          height={heightPerLine}
          style={{ marginBottom: i === lines - 1 ? 0 : "0.45rem" }}
        />
      ))}
    </div>
  );
}

type SkeletonTableProps = {
  rows?: number;
  columns?: number;
  headerLabels?: string[];
};

export function SkeletonTable({ rows = 6, columns = 4, headerLabels }: SkeletonTableProps) {
  return (
    <div className="card" style={{ padding: 0 }} aria-busy="true">
      <table>
        {headerLabels && (
          <thead>
            <tr>{headerLabels.map((h) => <th key={h}>{h}</th>)}</tr>
          </thead>
        )}
        <tbody>
          {Array.from({ length: rows }).map((_, i) => (
            <SkeletonRow key={i} columns={columns} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
