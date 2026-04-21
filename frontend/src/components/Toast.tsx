import React, { createContext, useContext, useState, useCallback, useEffect } from "react";

type ToastType = "success" | "error" | "info";
interface Toast { id: number; type: ToastType; message: string }
interface ToastContextValue { success: (msg: string) => void; error: (msg: string) => void; info: (msg: string) => void }

const ToastContext = createContext<ToastContextValue>({
  success: () => {}, error: () => {}, info: () => {},
});

export function useToast() { return useContext(ToastContext); }

let nextId = 0;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const add = useCallback((type: ToastType, message: string) => {
    const id = ++nextId;
    setToasts((prev) => [...prev.slice(-4), { id, type, message }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000);
  }, []);

  const value: ToastContextValue = {
    success: useCallback((msg: string) => add("success", msg), [add]),
    error: useCallback((msg: string) => add("error", msg), [add]),
    info: useCallback((msg: string) => add("info", msg), [add]),
  };

  const colors: Record<ToastType, string> = { success: "#10b981", error: "#ef4444", info: "#4f46e5" };
  const bgs: Record<ToastType, string> = { success: "#ecfdf5", error: "#fef2f2", info: "#eef2ff" };

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div style={{ position: "fixed", bottom: 20, right: 20, zIndex: 9999, display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        {toasts.map((t) => (
          <div
            key={t.id}
            style={{
              background: bgs[t.type], color: colors[t.type], border: `1px solid ${colors[t.type]}20`,
              padding: "0.65rem 1rem", borderRadius: 8, fontSize: "0.85rem", fontWeight: 500,
              boxShadow: "0 4px 12px rgba(0,0,0,0.1)", maxWidth: 350,
              animation: "slideIn 0.2s ease", display: "flex", alignItems: "center", gap: "0.5rem",
            }}
          >
            <span>{t.type === "success" ? "\u2713" : t.type === "error" ? "\u2717" : "\u2139"}</span>
            <span style={{ flex: 1 }}>{t.message}</span>
            <button onClick={() => setToasts((prev) => prev.filter((x) => x.id !== t.id))} style={{ background: "none", border: "none", cursor: "pointer", color: colors[t.type], opacity: 0.6, fontSize: "1rem" }}>&times;</button>
          </div>
        ))}
      </div>
      <style>{`@keyframes slideIn { from { opacity: 0; transform: translateX(20px); } to { opacity: 1; transform: translateX(0); } }`}</style>
    </ToastContext.Provider>
  );
}
