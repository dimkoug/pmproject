import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts";

interface Props {
  points: { date: string; remaining: number; done: number; ideal: number }[];
}

export default function BurndownChart({ points }: Props) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={points} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(v) => v.slice(5)} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e5e7eb" }} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Line type="monotone" dataKey="remaining" stroke="#4f46e5" strokeWidth={2} dot={false} name="Remaining" />
        <Line type="monotone" dataKey="done" stroke="#10b981" strokeWidth={2} dot={false} name="Done" />
        <Line type="monotone" dataKey="ideal" stroke="#9ca3af" strokeWidth={1.5} strokeDasharray="6 4" dot={false} name="Ideal" />
      </LineChart>
    </ResponsiveContainer>
  );
}
