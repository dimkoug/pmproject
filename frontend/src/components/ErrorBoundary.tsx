import React from "react";

interface Props { children: React.ReactNode; fallback?: React.ReactNode }
interface State { hasError: boolean; error?: Error }

export default class ErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "50vh", padding: "2rem", textAlign: "center" }}>
          <div style={{ fontSize: "2.5rem", marginBottom: "1rem", opacity: 0.2 }}>&#9888;</div>
          <h2 style={{ fontSize: "1.25rem", fontWeight: 600, color: "var(--gray-700)", marginBottom: "0.5rem" }}>Something went wrong</h2>
          <p style={{ color: "var(--gray-500)", fontSize: "0.9rem", marginBottom: "1.5rem" }}>{this.state.error?.message || "An unexpected error occurred"}</p>
          <button className="btn btn-primary" onClick={() => window.location.reload()}>Reload Page</button>
        </div>
      );
    }
    return this.props.children;
  }
}
