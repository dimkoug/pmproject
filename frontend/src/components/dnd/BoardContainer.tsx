import React, { useState } from "react";
import { DndContext, DragEndEvent, DragOverlay, DragStartEvent, PointerSensor, closestCorners, useSensor, useSensors } from "@dnd-kit/core";

interface Props {
  children: React.ReactNode;
  onDragEnd: (itemId: string, newColumnId: string) => void;
  renderOverlay?: (activeId: string) => React.ReactNode;
}

export default function BoardContainer({ children, onDragEnd, renderOverlay }: Props) {
  const [activeId, setActiveId] = useState<string | null>(null);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }));

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(String(event.active.id));
  };

  const handleDragEnd = (event: DragEndEvent) => {
    setActiveId(null);
    const { active, over } = event;
    if (!over) return;
    const itemId = String(active.id);
    const newColumn = String(over.id);
    if (itemId !== newColumn) {
      onDragEnd(itemId, newColumn);
    }
  };

  return (
    <DndContext sensors={sensors} collisionDetection={closestCorners} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
      {children}
      <DragOverlay>
        {activeId && renderOverlay ? renderOverlay(activeId) : null}
      </DragOverlay>
    </DndContext>
  );
}
