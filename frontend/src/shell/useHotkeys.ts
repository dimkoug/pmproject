import { useEffect } from "react";

export type HotkeyHandler = (e: KeyboardEvent) => void;

export type Hotkey = {
  combo: string;
  handler: HotkeyHandler;
  allowInInputs?: boolean;
  description?: string;
};

const isEditableTarget = (t: EventTarget | null): boolean => {
  if (!t || !(t instanceof HTMLElement)) return false;
  const tag = t.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  if (t.isContentEditable) return true;
  return false;
};

const normalizeCombo = (combo: string): string =>
  combo
    .toLowerCase()
    .split("+")
    .map((s) => s.trim())
    .sort()
    .join("+");

const eventToCombo = (e: KeyboardEvent): string => {
  const parts: string[] = [];
  if (e.ctrlKey || e.metaKey) parts.push("ctrl");
  if (e.altKey) parts.push("alt");
  if (e.shiftKey) parts.push("shift");
  const k = e.key.toLowerCase();
  if (k !== "control" && k !== "meta" && k !== "alt" && k !== "shift") parts.push(k);
  return parts.sort().join("+");
};

export function useHotkeys(hotkeys: Hotkey[]) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const editable = isEditableTarget(e.target);
      const combo = eventToCombo(e);
      for (const hk of hotkeys) {
        if (editable && !hk.allowInInputs) continue;
        if (normalizeCombo(hk.combo) === combo) {
          hk.handler(e);
        }
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [hotkeys]);
}
