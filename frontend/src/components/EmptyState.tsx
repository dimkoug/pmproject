import React from "react";

interface Props {
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export default function EmptyState({ title, description, action }: Props) {
  return (
    <div style={{ textAlign: "center", padding: "3.5rem 2rem", color: "var(--gray-400)" }}>
      <div style={{ fontSize: "2.5rem", marginBottom: "0.75rem", opacity: 0.2 }}>&#9776;</div>
      <p style={{ fontSize: "0.95rem", fontWeight: 500, color: "var(--gray-500)", marginBottom: "0.35rem" }}>{title}</p>
      {description && <p style={{ fontSize: "0.85rem", marginBottom: "1rem" }}>{description}</p>}
      {action}
    </div>
  );
}
