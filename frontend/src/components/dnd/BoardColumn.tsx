import React from "react";
import { useDroppable } from "@dnd-kit/core";

interface Props {
  id: string;
  title: string;
  count: number;
  children: React.ReactNode;
}

export default function BoardColumn({ id, title, count, children }: Props) {
  const { setNodeRef, isOver } = useDroppable({ id });

  return (
    <div
      ref={setNodeRef}
      className="board-column"
      style={{
        background: isOver ? "var(--primary-light)" : undefined,
        borderColor: isOver ? "var(--primary)" : undefined,
        transition: "background 0.15s, border-color 0.15s",
      }}
    >
      <h4>{title} ({count})</h4>
      {children}
    </div>
  );
}
