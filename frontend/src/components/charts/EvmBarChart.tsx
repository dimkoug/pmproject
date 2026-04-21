import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from "recharts";

interface Props {
  bac: number;
  pv: number;
  ev: number;
  ac: number;
}

const COLORS: Record<string, string> = {
  BAC: "#6b7280",
  PV: "#4f46e5",
  EV: "#10b981",
  AC: "#f59e0b",
};

export default function EvmBarChart({ bac, pv, ev, ac }: Props) {
  const data = [
    { name: "BAC", value: bac },
    { name: "PV", value: pv },
    { name: "EV", value: ev },
    { name: "AC", value: ac },
  ];

  return (
    <ResponsiveContainer width="100%" height={250}>
      <BarChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="name" tick={{ fontSize: 12, fontWeight: 600 }} />
        <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
        <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} formatter={(v: any) => `$${Number(v).toLocaleString()}`} />
        <Bar dataKey="value" radius={[4, 4, 0, 0]} barSize={50}>
          {data.map((entry) => (
            <Cell key={entry.name} fill={COLORS[entry.name]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
