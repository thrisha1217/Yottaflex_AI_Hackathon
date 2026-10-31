import { useState } from "react";
import { useCasesOverTime, useTopAssessments, useOutcomesByProgram } from "../hooks/useAnalytics";
import { CasesOverTimeChart } from "../components/charts/CasesOverTimeChart";
import { TopAssessmentsChart } from "../components/charts/TopAssessmentsChart";
import { OutcomesByProgramChart } from "../components/charts/OutcomesByProgramChart";
import { Spinner } from "../components/Spinner";
import { ErrorMessage } from "../components/ErrorMessage";

export function AnalyticsPage() {
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");

  // Only pass params when values are set
  const timeParams = {};
  if (fromDate) timeParams.from_date = fromDate;
  if (toDate) timeParams.to_date = toDate;

  const { data: casesOverTime, loading: cotLoading, error: cotError } = useCasesOverTime(timeParams);
  const { data: topAssessments, loading: taLoading, error: taError } = useTopAssessments();
  const { data: outcomesByProgram, loading: obpLoading, error: obpError } = useOutcomesByProgram();

  return (
    <div style={{ padding: "1.5rem", maxWidth: "1200px", margin: "0 auto" }}>
      <h1 style={{ marginBottom: "1.5rem", fontSize: "1.75rem", fontWeight: 600 }}>Analytics</h1>

      {/* DateRangeSelector */}
      <div
        style={{
          display: "flex",
          gap: "1.5rem",
          alignItems: "center",
          padding: "1rem",
          backgroundColor: "#f5f5f5",
          borderRadius: "6px",
          marginBottom: "2rem",
          flexWrap: "wrap",
        }}
      >
        <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.9rem" }}>
          <span style={{ fontWeight: 500 }}>From:</span>
          <input
            type="date"
            value={fromDate}
            onChange={(e) => setFromDate(e.target.value)}
            style={{
              padding: "0.375rem 0.5rem",
              border: "1px solid #ccc",
              borderRadius: "4px",
              fontSize: "0.9rem",
            }}
          />
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.9rem" }}>
          <span style={{ fontWeight: 500 }}>To:</span>
          <input
            type="date"
            value={toDate}
            onChange={(e) => setToDate(e.target.value)}
            style={{
              padding: "0.375rem 0.5rem",
              border: "1px solid #ccc",
              borderRadius: "4px",
              fontSize: "0.9rem",
            }}
          />
        </label>
        {(fromDate || toDate) && (
          <button
            onClick={() => { setFromDate(""); setToDate(""); }}
            style={{
              padding: "0.375rem 0.75rem",
              border: "1px solid #ccc",
              borderRadius: "4px",
              backgroundColor: "#fff",
              cursor: "pointer",
              fontSize: "0.875rem",
              color: "#555",
            }}
          >
            Clear
          </button>
        )}
      </div>

      {/* Cases Over Time */}
      <section style={{ marginBottom: "2.5rem" }}>
        <h2 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "1rem" }}>Cases Over Time</h2>
        {cotLoading ? (
          <div style={{ display: "flex", justifyContent: "center", padding: "2rem" }}>
            <Spinner />
          </div>
        ) : cotError ? (
          <ErrorMessage error={cotError} />
        ) : (
          <CasesOverTimeChart data={casesOverTime?.data} />
        )}
      </section>

      {/* Top Assessments */}
      <section style={{ marginBottom: "2.5rem" }}>
        <h2 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "1rem" }}>
          Top Assessments by Case Count
        </h2>
        {taLoading ? (
          <div style={{ display: "flex", justifyContent: "center", padding: "2rem" }}>
            <Spinner />
          </div>
        ) : taError ? (
          <ErrorMessage error={taError} />
        ) : (
          <TopAssessmentsChart data={topAssessments?.data} />
        )}
      </section>

      {/* Outcomes by Program */}
      <section style={{ marginBottom: "2.5rem" }}>
        <h2 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "1rem" }}>
          Outcomes by Program
        </h2>
        {obpLoading ? (
          <div style={{ display: "flex", justifyContent: "center", padding: "2rem" }}>
            <Spinner />
          </div>
        ) : obpError ? (
          <ErrorMessage error={obpError} />
        ) : (
          <OutcomesByProgramChart data={outcomesByProgram?.data} />
        )}
      </section>
    </div>
  );
}
