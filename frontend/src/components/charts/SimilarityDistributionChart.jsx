import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

/**
 * SimilarityDistributionChart
 *
 * Renders a bar chart showing the distribution of similarity scores across
 * score buckets (e.g. "0-10", "11-20", …, "91-100").
 *
 * @param {{ data: Array<{ bucket: string, count: number }> | null | undefined }} props
 */
export function SimilarityDistributionChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <div
        style={{
          height: 300,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#888",
          fontSize: 14,
        }}
      >
        No data available
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data}>
        <XAxis dataKey="bucket" />
        <YAxis />
        <Tooltip />
        <Bar dataKey="count" fill="#4f86c6" />
      </BarChart>
    </ResponsiveContainer>
  );
}
