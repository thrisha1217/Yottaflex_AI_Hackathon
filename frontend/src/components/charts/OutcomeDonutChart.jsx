import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from "recharts";

/** Colour map for each decision outcome */
const COLORS = {
  NO_VIOLATION: "#4caf50",  // green
  VIOLATION: "#f44336",      // red
  INCONCLUSIVE: "#ff9800",   // orange
};

/**
 * OutcomeDonutChart — donut chart visualising decision outcome distribution.
 *
 * Props:
 *   data  {Array}  — array of `{ name: string, value: number }` objects where
 *                    `name` is one of "NO_VIOLATION" | "VIOLATION" | "INCONCLUSIVE"
 *
 * Validates: Requirements 17.1
 */
export function OutcomeDonutChart({ data }) {
  if (!data || data.length === 0) {
    return <p>No data available</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          innerRadius={60}
          outerRadius={100}
          paddingAngle={3}
        >
          {data.map((entry) => (
            <Cell
              key={entry.name}
              fill={COLORS[entry.name] ?? "#9e9e9e"}
            />
          ))}
        </Pie>
        <Tooltip />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}

export default OutcomeDonutChart;
