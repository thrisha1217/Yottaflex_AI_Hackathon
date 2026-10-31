import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

/**
 * OutcomesByProgramChart
 *
 * Renders a horizontal stacked bar chart showing case outcomes broken down by program.
 *
 * @param {{ data: Array<{ program: string, NO_VIOLATION: number, VIOLATION: number, INCONCLUSIVE: number }> }} props
 *   data — array of outcome counts per program,
 *   e.g. [{ program: "Computer Science", NO_VIOLATION: 40, VIOLATION: 10, INCONCLUSIVE: 5 }]
 */
export function OutcomesByProgramChart({ data }) {
  if (!data || data.length === 0) return <p>No data available</p>;

  return (
    <ResponsiveContainer width="100%" height={400}>
      <BarChart data={data} layout="vertical">
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis type="number" />
        <YAxis
          type="category"
          dataKey="program"
          width={160}
          tick={{ fontSize: 11 }}
        />
        <Tooltip />
        <Legend />
        <Bar dataKey="NO_VIOLATION" name="No Violation" stackId="a" fill="#4caf50" />
        <Bar dataKey="VIOLATION" name="Violation" stackId="a" fill="#f44336" />
        <Bar dataKey="INCONCLUSIVE" name="Inconclusive" stackId="a" fill="#ff9800" />
      </BarChart>
    </ResponsiveContainer>
  );
}
