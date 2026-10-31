import React from "react";
import { useSummary, useSimilarityDistribution } from "../hooks/useAnalytics";
import { SimilarityDistributionChart } from "../components/charts/SimilarityDistributionChart";
import { Spinner } from "../components/Spinner";
import { ErrorMessage } from "../components/ErrorMessage";
import { ErrorBoundary } from "../components/ErrorBoundary";

// ─── Card styles ─────────────────────────────────────────────────────────────

const cardStyle = {
  padding: "1.25rem 1.5rem",
  border: "1px solid #e0e0e0",
  borderRadius: "8px",
  backgroundColor: "#fff",
  minWidth: "160px",
  flex: "1 1 160px",
  boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
};

const cardLabelStyle = {
  margin: "0 0 0.5rem 0",
  fontSize: "0.85rem",
  fontWeight: 600,
  color: "#555",
  textTransform: "uppercase",
  letterSpacing: "0.04em",
};

const cardValueStyle = {
  margin: 0,
  fontSize: "2rem",
  fontWeight: 700,
  color: "#1976d2",
};

// ─── Sub-components ───────────────────────────────────────────────────────────

/**
 * SubmissionSummaryCard — displays total submissions count.
 * Validates: Requirements 15.1
 */
function SubmissionSummaryCard({ value }) {
  return (
    <div style={cardStyle} aria-label="Total Submissions">
      <h3 style={cardLabelStyle}>Total Submissions</h3>
      <p style={cardValueStyle}>{value ?? "—"}</p>
    </div>
  );
}

/**
 * FlaggedSummaryCard — displays total flagged submissions count.
 * Validates: Requirements 15.2
 */
function FlaggedSummaryCard({ value }) {
  return (
    <div style={cardStyle} aria-label="Flagged Submissions">
      <h3 style={cardLabelStyle}>Flagged Submissions</h3>
      <p style={{ ...cardValueStyle, color: "#d32f2f" }}>{value ?? "—"}</p>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

/**
 * DashboardPage — top-level analytics overview.
 *
 * Displays:
 *   • Summary stat cards (total submissions, flagged, cases, decisions, appeals)
 *   • Similarity score distribution bar chart
 *
 * All data fetches are wrapped in an ErrorBoundary; individual loading/error
 * states are handled inline so a failure in one section does not block others.
 *
 * Validates: Requirements 15.1, 15.2, 15.3, 15.4, 15.5
 */
export function DashboardPage() {
  const {
    data: summary,
    loading: summaryLoading,
    error: summaryError,
  } = useSummary();

  const {
    data: distribution,
    loading: distLoading,
    error: distError,
  } = useSimilarityDistribution();

  return (
    <div style={{ padding: "1.5rem", maxWidth: "1200px", margin: "0 auto" }}>
      <h1 style={{ marginBottom: "1.5rem", fontSize: "1.75rem", fontWeight: 700 }}>
        Dashboard
      </h1>

      <ErrorBoundary>
        {/* ── Summary cards ── */}
        <section aria-label="Summary statistics" style={{ marginBottom: "2rem" }}>
          <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "0.75rem", color: "#333" }}>
            Overview
          </h2>

          {summaryLoading ? (
            <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <Spinner />
              <span style={{ color: "#666", fontSize: "0.9rem" }}>Loading summary…</span>
            </div>
          ) : summaryError ? (
            <ErrorMessage error={summaryError} />
          ) : (
            <div
              style={{
                display: "flex",
                gap: "1rem",
                flexWrap: "wrap",
              }}
            >
              {/* Requirements 15.1 */}
              <SubmissionSummaryCard value={summary?.total_submissions} />

              {/* Requirements 15.2 */}
              <FlaggedSummaryCard value={summary?.flagged_submissions} />

              {/* Requirements 15.3 */}
              <div style={cardStyle} aria-label="Total Cases">
                <h3 style={cardLabelStyle}>Total Cases</h3>
                <p style={cardValueStyle}>{summary?.total_cases ?? "—"}</p>
              </div>

              {/* Requirements 15.4 */}
              <div style={cardStyle} aria-label="Total Decisions">
                <h3 style={cardLabelStyle}>Total Decisions</h3>
                <p style={cardValueStyle}>{summary?.total_decisions ?? "—"}</p>
              </div>

              {/* Requirements 15.5 */}
              <div style={cardStyle} aria-label="Total Appeals">
                <h3 style={cardLabelStyle}>Total Appeals</h3>
                <p style={cardValueStyle}>{summary?.total_appeals ?? "—"}</p>
              </div>
            </div>
          )}
        </section>

        {/* ── Similarity distribution chart ── */}
        <section aria-label="Similarity score distribution">
          <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "0.75rem", color: "#333" }}>
            Similarity Score Distribution
          </h2>

          {distLoading ? (
            <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <Spinner />
              <span style={{ color: "#666", fontSize: "0.9rem" }}>Loading chart…</span>
            </div>
          ) : distError ? (
            <ErrorMessage error={distError} />
          ) : (
            <div
              style={{
                padding: "1rem",
                border: "1px solid #e0e0e0",
                borderRadius: "8px",
                backgroundColor: "#fff",
                boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
              }}
            >
              <SimilarityDistributionChart data={distribution?.data} />
            </div>
          )}
        </section>

        {/*
          OutcomeDonutChart is not rendered here because the /analytics/summary
          endpoint does not return per-outcome counts. Outcome breakdown is
          available on the dedicated Analytics page via /analytics/outcomes-by-program.
        */}
      </ErrorBoundary>
    </div>
  );
}

export default DashboardPage;
