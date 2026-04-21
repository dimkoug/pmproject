import { useGetBalanceSheetQuery } from "../../services/api";
import PageHeader from "../../shell/PageHeader";

export default function BalanceSheetPage() {
  const { data: bs } = useGetBalanceSheetQuery();
  if (!bs) return <div>Loading…</div>;

  return (
    <div>
      <PageHeader title="Balance sheet" subtitle="Assets, liabilities, and equity." />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
        <div className="card">
          <h3>Assets</h3>
          <table>
            <tbody>
              {bs.assets?.map((a: any) => (
                <tr key={a.code}>
                  <td style={{ fontFamily: "monospace" }}>{a.code}</td>
                  <td>{a.name}</td>
                  <td style={{ textAlign: "right" }}>${a.balance?.toLocaleString()}</td>
                </tr>
              ))}
              <tr style={{ borderTop: "2px solid var(--gray-300)", fontWeight: 700 }}>
                <td colSpan={2}>Total assets</td>
                <td style={{ textAlign: "right" }}>${bs.total_assets?.toLocaleString()}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div>
          <div className="card">
            <h3>Liabilities</h3>
            <table>
              <tbody>
                {bs.liabilities?.map((a: any) => (
                  <tr key={a.code}>
                    <td style={{ fontFamily: "monospace" }}>{a.code}</td>
                    <td>{a.name}</td>
                    <td style={{ textAlign: "right" }}>${a.balance?.toLocaleString()}</td>
                  </tr>
                ))}
                <tr style={{ borderTop: "2px solid var(--gray-300)", fontWeight: 700 }}>
                  <td colSpan={2}>Total liabilities</td>
                  <td style={{ textAlign: "right" }}>${bs.total_liabilities?.toLocaleString()}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div className="card" style={{ marginTop: "1rem" }}>
            <h3>Equity</h3>
            <table>
              <tbody>
                {bs.equity?.map((a: any) => (
                  <tr key={a.code}>
                    <td style={{ fontFamily: "monospace" }}>{a.code}</td>
                    <td>{a.name}</td>
                    <td style={{ textAlign: "right" }}>${a.balance?.toLocaleString()}</td>
                  </tr>
                ))}
                <tr style={{ borderTop: "2px solid var(--gray-300)", fontWeight: 700 }}>
                  <td colSpan={2}>Total equity</td>
                  <td style={{ textAlign: "right" }}>${bs.total_equity?.toLocaleString()}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
