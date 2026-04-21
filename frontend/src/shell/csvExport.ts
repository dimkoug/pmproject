/** Authenticated CSV download helper — the export endpoints require a Bearer
 * token, so we fetch the blob with headers and trigger a client-side download
 * rather than linking to an <a href>. */

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function downloadCsv(domain: string): Promise<void> {
  const token = localStorage.getItem("token");
  const res = await fetch(`${API_URL}/api/export/${domain}.csv`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    alert(`Export failed: ${res.status}`);
    return;
  }
  const disposition = res.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename=([^;]+)/);
  const filename = match ? match[1].trim() : `${domain}.csv`;
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
