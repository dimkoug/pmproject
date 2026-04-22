import { describe, it, expect, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useFileDropTarget } from "../shell/useFileDropTarget";

function makeDragEvent(types: string[], files: File[] = []) {
  const dataTransfer = {
    types,
    files: files as unknown as FileList,
    dropEffect: "none",
  };
  return {
    preventDefault: vi.fn(),
    dataTransfer,
  } as unknown as React.DragEvent;
}

describe("useFileDropTarget", () => {
  it("initially not over", () => {
    const { result } = renderHook(() => useFileDropTarget(() => {}));
    expect(result.current.isOver).toBe(false);
  });

  it("drag enter with files sets isOver true and prevents default", () => {
    const { result } = renderHook(() => useFileDropTarget(() => {}));
    const evt = makeDragEvent(["Files"]);
    act(() => {
      result.current.dragHandlers.onDragEnter(evt);
    });
    expect(result.current.isOver).toBe(true);
    expect(evt.preventDefault).toHaveBeenCalled();
  });

  it("drag enter without Files type is ignored", () => {
    const { result } = renderHook(() => useFileDropTarget(() => {}));
    const evt = makeDragEvent(["text/plain"]);
    act(() => {
      result.current.dragHandlers.onDragEnter(evt);
    });
    expect(result.current.isOver).toBe(false);
  });

  it("drop fires onFiles callback with the dropped files", () => {
    const onFiles = vi.fn();
    const { result } = renderHook(() => useFileDropTarget(onFiles));
    const file = new File(["data"], "test.txt", { type: "text/plain" });
    const evt = makeDragEvent(["Files"], [file]);
    act(() => {
      result.current.dragHandlers.onDrop(evt);
    });
    expect(onFiles).toHaveBeenCalledOnce();
    expect(onFiles.mock.calls[0][0][0].name).toBe("test.txt");
  });

  it("drop without files does not call callback", () => {
    const onFiles = vi.fn();
    const { result } = renderHook(() => useFileDropTarget(onFiles));
    const evt = makeDragEvent(["Files"], []);
    act(() => {
      result.current.dragHandlers.onDrop(evt);
    });
    expect(onFiles).not.toHaveBeenCalled();
  });

  it("depth counter: enter twice + leave once still over", () => {
    const { result } = renderHook(() => useFileDropTarget(() => {}));
    act(() => {
      result.current.dragHandlers.onDragEnter(makeDragEvent(["Files"]));
      result.current.dragHandlers.onDragEnter(makeDragEvent(["Files"]));
      result.current.dragHandlers.onDragLeave(makeDragEvent([]));
    });
    expect(result.current.isOver).toBe(true);
  });

  it("depth counter: enter + leave back to not-over", () => {
    const { result } = renderHook(() => useFileDropTarget(() => {}));
    act(() => {
      result.current.dragHandlers.onDragEnter(makeDragEvent(["Files"]));
      result.current.dragHandlers.onDragLeave(makeDragEvent([]));
    });
    expect(result.current.isOver).toBe(false);
  });

  it("drop resets depth to zero", () => {
    const { result } = renderHook(() => useFileDropTarget(() => {}));
    const file = new File(["x"], "x.txt");
    act(() => {
      result.current.dragHandlers.onDragEnter(makeDragEvent(["Files"]));
      result.current.dragHandlers.onDragEnter(makeDragEvent(["Files"]));
      result.current.dragHandlers.onDrop(makeDragEvent(["Files"], [file]));
    });
    expect(result.current.isOver).toBe(false);
  });
});
