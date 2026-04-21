const sizes = { sm: 20, md: 32, lg: 48 };

export default function Spinner({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
  const s = sizes[size];
  return (
    <div style={{ display: "flex", justifyContent: "center", padding: "2rem 0" }}>
      <div
        style={{
          width: s, height: s, border: `3px solid var(--gray-200)`,
          borderTopColor: "var(--primary)", borderRadius: "50%",
          animation: "spin 0.7s linear infinite",
        }}
      />
      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
    </div>
  );
}
