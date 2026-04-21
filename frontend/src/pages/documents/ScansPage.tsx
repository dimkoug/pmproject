import { useGetScanResultsQuery, useScanVersionMutation } from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";

export default function ScansPage() {
  const { data: scans = [], refetch } = useGetScanResultsQuery();
  const [scanVersion] = useScanVersionMutation();

  return (
    <div>
      <PageHeader title="Virus scan results" subtitle="Per-version malware scan history." />
      <CommandBar
        items={[
          {
            key: "scan", label: "Scan version",
            onClick: async () => {
              const vid = prompt("Version ID to scan:"); if (!vid) return;
              const r: any = await scanVersion(vid);
              alert(`Status: ${r.data?.status}${r.data?.details ? " — " + r.data.details : ""}`);
              refetch();
            },
          },
        ]}
      />
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>Version</th><th>Status</th><th>Details</th><th>Scanned at</th></tr></thead>
          <tbody>
            {scans.map((s: any) => (
              <tr key={s.id}>
                <td style={{ fontSize: "0.75rem" }}>{s.version_id.slice(0, 8)}…</td>
                <td><span className={`badge ${s.status === "clean" ? "badge-green" : s.status === "infected" ? "badge-red" : "badge-gray"}`}>{s.status}</span></td>
                <td style={{ fontSize: "0.82rem" }}>{s.details || "—"}</td>
                <td style={{ fontSize: "0.82rem" }}>{s.scanned_at ? new Date(s.scanned_at).toLocaleString() : ""}</td>
              </tr>
            ))}
            {scans.length === 0 && <tr><td colSpan={4} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No scans yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
