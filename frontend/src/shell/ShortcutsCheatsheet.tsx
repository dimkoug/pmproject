import { createPortal } from "react-dom";
import { Icon } from "./icons";

export type ShortcutsCheatsheetProps = {
  open: boolean;
  onClose: () => void;
};

type Row = { keys: string[]; label: string };

const ROWS: { title: string; rows: Row[] }[] = [
  {
    title: "Global",
    rows: [
      { keys: ["Ctrl", "K"], label: "Focus global search" },
      { keys: ["/"], label: "Focus search (when not typing)" },
      { keys: ["Esc"], label: "Close modal, drawer, or panel" },
      { keys: ["?"], label: "Open this cheat sheet" },
    ],
  },
  {
    title: "List pages",
    rows: [
      { keys: ["N"], label: "Create new item" },
    ],
  },
];

export default function ShortcutsCheatsheet({ open, onClose }: ShortcutsCheatsheetProps) {
  if (!open) return null;
  const node = (
    <div
      className="form-modal-root"
      role="dialog"
      aria-modal="true"
      aria-label="Keyboard shortcuts"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="form-modal-panel" style={{ maxWidth: 520 }}>
        <header className="form-modal-head">
          <h2 className="form-modal-title">Keyboard shortcuts</h2>
          <button type="button" className="form-modal-close" onClick={onClose} aria-label="Close">
            <Icon.Close size={16} />
          </button>
        </header>
        <div className="form-modal-body">
          {ROWS.map((section) => (
            <div key={section.title} className="cheatsheet-section">
              <div className="cheatsheet-section-title">{section.title}</div>
              <ul className="cheatsheet-list">
                {section.rows.map((r) => (
                  <li key={r.label} className="cheatsheet-row">
                    <span className="cheatsheet-label">{r.label}</span>
                    <span className="cheatsheet-keys">
                      {r.keys.map((k, i) => (
                        <kbd key={i} className="cheatsheet-kbd">{k}</kbd>
                      ))}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <footer className="form-modal-foot">
          <button type="button" className="btn btn-sm btn-primary" onClick={onClose}>Got it</button>
        </footer>
      </div>
    </div>
  );
  return createPortal(node, document.body);
}
