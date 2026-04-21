import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine } from "recharts";

interface Props {
  sprints: { sprint: string; points: number }[];
  average: number;
}

export default function VelocityChart({ sprints, average }: Props) {
  return (
    <ResponsiveContainer width="100%" height={250}>
      <BarChart data={sprints} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="sprint" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
        <Bar dataKey="points" fill="#4f46e5" radius={[4, 4, 0, 0]} barSize={40} name="Story Points" />
        {average > 0 && (
          <ReferenceLine
            y={average}
            stroke="#f59e0b"
            strokeWidth={2}
            strokeDasharray="6 4"
            label={{ value: `Avg: ${average}`, fill: "#f59e0b", fontSize: 11, position: "right" }}
          />
        )}
      </BarChart>
    </ResponsiveContainer>
  );
}
