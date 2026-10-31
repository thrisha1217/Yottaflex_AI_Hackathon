import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

/**
 * TopAssessmentsChart
 *
 * Renders a horizontal bar chart showing the top 10 assessments by number of
 * integrity cases raised against them.
 *
 * @param {{ data: Array<{ title: string, case_count: number }> | null | undefined }} props
 */
export function TopAssessmentsChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <div
        style={{
          height: 350,
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
    <ResponsiveContainer width="100%" height={350}>
      <BarChart data={data} layout="horizontal">
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="title" tick={{ fontSize: 11 }} />
        <YAxis />
        <Tooltip />
        <Bar dataKey="case_count" fill="#ff7043" />
      </BarChart>
    </ResponsiveContainer>
  );
}
