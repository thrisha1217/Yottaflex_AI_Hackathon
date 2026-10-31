import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

/**
 * CasesOverTimeChart
 *
 * Renders a line chart showing the number of integrity cases per month.
 *
 * @param {{ data: Array<{ month: string, count: number }> }} props
 *   data — array of monthly case counts, e.g. [{ month: "2026-01", count: 24 }, ...]
 */
export function CasesOverTimeChart({ data }) {
  if (!data || data.length === 0) return <p>No data available</p>;

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="month" />
        <YAxis />
        <Tooltip />
        <Line
          type="monotone"
          dataKey="count"
          stroke="#1976d2"
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
