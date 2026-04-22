import { useCallback, useRef, useState } from "react";

type Handlers = {
  onDragEnter: (e: React.DragEvent) => void;
  onDragOver: (e: React.DragEvent) => void;
  onDragLeave: (e: React.DragEvent) => void;
  onDrop: (e: React.DragEvent) => void;
};

/**
 * Drag-and-drop file target. Spread the returned `dragHandlers` onto the
 * element that should accept drops; read `isOver` to render a visual
 * overlay. The `onFiles` callback fires with the dropped FileList.
 *
 * Uses a depth counter so `onDragLeave` on a child element doesn't flicker
 * the "over" state off while the pointer is still inside the root.
 */
export function useFileDropTarget(onFiles: (files: FileList) => void): { isOver: boolean; dragHandlers: Handlers } {
  const [isOver, setIsOver] = useState(false);
  const depth = useRef(0);

  const onDragEnter = useCallback((e: React.DragEvent) => {
    if (!Array.from(e.dataTransfer?.types ?? []).includes("Files")) return;
    e.preventDefault();
    depth.current += 1;
    setIsOver(true);
  }, []);

  const onDragOver = useCallback((e: React.DragEvent) => {
    if (!Array.from(e.dataTransfer?.types ?? []).includes("Files")) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
  }, []);

  const onDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    depth.current = Math.max(0, depth.current - 1);
    if (depth.current === 0) setIsOver(false);
  }, []);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    depth.current = 0;
    setIsOver(false);
    const files = e.dataTransfer?.files;
    if (files && files.length > 0) onFiles(files);
  }, [onFiles]);

  return { isOver, dragHandlers: { onDragEnter, onDragOver, onDragLeave, onDrop } };
}
