import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine } from "recharts";

interface Props {
  buckets: { bucket: string; count: number }[];
  p50?: number;
  p90?: number;
}

export default function HistogramChart({ buckets, p50, p90 }: Props) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={buckets} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="bucket" tick={{ fontSize: 10 }} angle={-25} textAnchor="end" height={50} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
        <Bar dataKey="count" fill="#4f46e5" radius={[3, 3, 0, 0]} opacity={0.8} name="Simulations" />
        {p50 && <ReferenceLine x={p50} stroke="#10b981" strokeWidth={2} strokeDasharray="4 4" label={{ value: "P50", fill: "#10b981", fontSize: 11 }} />}
        {p90 && <ReferenceLine x={p90} stroke="#ef4444" strokeWidth={2} strokeDasharray="4 4" label={{ value: "P90", fill: "#ef4444", fontSize: 11 }} />}
      </BarChart>
    </ResponsiveContainer>
  );
}
