import React from "react";
import {
  useConflictReassignments,
  usePostDecisionEvidence,
  useAppealsWithoutIndependentReview,
} from "../hooks/useAudit";
import { Spinner } from "../components/Spinner";
import { ErrorMessage } from "../components/ErrorMessage";

// ─── Helpers ────────────────────────────────────────────────────────────────

function formatDateTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return isNaN(d.getTime()) ? value : d.toLocaleString();
}

// ─── Shared styles ───────────────────────────────────────────────────────────

const tableStyle = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: "0.875rem",
};

const thStyle = {
  textAlign: "left",
  padding: "0.625rem 0.75rem",
  backgroundColor: "#f3f4f6",
  borderBottom: "2px solid #e5e7eb",
  fontWeight: 600,
  color: "#374151",
  whiteSpace: "nowrap",
};

const tdStyle = {
  padding: "0.5rem 0.75rem",
  borderBottom: "1px solid #e5e7eb",
  color: "#1f2937",
  verticalAlign: "top",
};

const sectionStyle = {
  marginBottom: "2.5rem",
};

const sectionHeadingStyle = {
  fontSize: "1.15rem",
  fontWeight: 600,
  marginBottom: "0.75rem",
  color: "#111827",
};

const tableWrapperStyle = {
  overflowX: "auto",
  border: "1px solid #e5e7eb",
  borderRadius: "6px",
};

const emptyStyle = {
  padding: "1.5rem",
  textAlign: "center",
  color: "#6b7280",
  fontSize: "0.875rem",
};

// ─── ConflictReassignmentsTable ──────────────────────────────────────────────

/**
 * Displays cases where a conflict of interest triggered a reviewer reassignment.
 * Columns: case_id, reviewer_id, reviewer_name, conflict_reason, assigned_at, unassigned_at
 */
function ConflictReassignmentsTable({ data, error }) {
  return (
    <section style={sectionStyle} aria-labelledby="conflict-reassignments-heading">
      <h2 id="conflict-reassignments-heading" style={sectionHeadingStyle}>
        Conflict of Interest Reassignments
      </h2>
      {error && <ErrorMessage error={error} />}
      <div style={tableWrapperStyle}>
        {!error && data.length === 0 ? (
          <p style={emptyStyle}>No conflict reassignments found.</p>
        ) : (
          <table style={tableStyle} aria-label="Conflict of interest reassignments">
            <thead>
              <tr>
                <th style={thStyle}>Case ID</th>
                <th style={thStyle}>Reviewer ID</th>
                <th style={thStyle}>Reviewer Name</th>
                <th style={thStyle}>Conflict Reason</th>
                <th style={thStyle}>Assigned At</th>
                <th style={thStyle}>Unassigned At</th>
              </tr>
            </thead>
            <tbody>
              {data.map((row, idx) => (
                <tr
                  key={row.assignment_id ?? idx}
                  style={idx % 2 === 1 ? { backgroundColor: "#f9fafb" } : undefined}
                >
                  <td style={tdStyle}>{row.case_id ?? "—"}</td>
                  <td style={tdStyle}>{row.reviewer_id ?? "—"}</td>
                  <td style={tdStyle}>{row.reviewer_name ?? "—"}</td>
                  <td style={tdStyle}>{row.conflict_reason ?? "—"}</td>
                  <td style={tdStyle}>{formatDateTime(row.assigned_at)}</td>
                  <td style={tdStyle}>{formatDateTime(row.unassigned_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}

// ─── PostDecisionEvidenceTable ───────────────────────────────────────────────

/**
 * Displays evidence submitted after a decision, grouped visually by case_id.
 * Columns: evidence_id, evidence_type, added_at  (with case_id group header rows)
 */
function PostDecisionEvidenceTable({ data, error }) {
  // Group rows by case_id while preserving original order of first occurrence
  const groupedEntries = React.useMemo(() => {
    const map = new Map();
    for (const row of data) {
      const key = row.case_id;
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(row);
    }
    return Array.from(map.entries()); // [[case_id, [rows…]], …]
  }, [data]);

  return (
    <section style={sectionStyle} aria-labelledby="post-decision-evidence-heading">
      <h2 id="post-decision-evidence-heading" style={sectionHeadingStyle}>
        Post-Decision Evidence
      </h2>
      {error && <ErrorMessage error={error} />}
      <div style={tableWrapperStyle}>
        {!error && groupedEntries.length === 0 ? (
          <p style={emptyStyle}>No post-decision evidence found.</p>
        ) : (
          <table style={tableStyle} aria-label="Post-decision evidence grouped by case">
            <thead>
              <tr>
                <th style={thStyle}>Case ID</th>
                <th style={thStyle}>Evidence ID</th>
                <th style={thStyle}>Evidence Type</th>
                <th style={thStyle}>Added At</th>
              </tr>
            </thead>
            <tbody>
              {groupedEntries.map(([caseId, rows]) =>
                rows.map((row, rowIdx) => (
                  <tr
                    key={row.evidence_id ?? `${caseId}-${rowIdx}`}
                    style={rowIdx % 2 === 1 ? { backgroundColor: "#f9fafb" } : undefined}
                  >
                    {/* Show case_id only on the first row of each group */}
                    {rowIdx === 0 ? (
                      <td
                        style={{ ...tdStyle, fontWeight: 600 }}
                        rowSpan={rows.length}
                      >
                        {caseId ?? "—"}
                      </td>
                    ) : null}
                    <td style={tdStyle}>{row.evidence_id ?? "—"}</td>
                    <td style={tdStyle}>{row.evidence_type ?? "—"}</td>
                    <td style={tdStyle}>{formatDateTime(row.added_at)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}

// ─── AppealsWithoutIndependentReviewTable ────────────────────────────────────

/**
 * Displays appeals that have no independent reviewer assigned.
 * Columns: appeal_id, case_id, appeal_status, submitted_at
 */
function AppealsWithoutIndependentReviewTable({ data, error }) {
  return (
    <section style={sectionStyle} aria-labelledby="appeals-no-review-heading">
      <h2 id="appeals-no-review-heading" style={sectionHeadingStyle}>
        Appeals Without Independent Review
      </h2>
      {error && <ErrorMessage error={error} />}
      <div style={tableWrapperStyle}>
        {!error && data.length === 0 ? (
          <p style={emptyStyle}>No appeals without independent review found.</p>
        ) : (
          <table style={tableStyle} aria-label="Appeals without independent review">
            <thead>
              <tr>
                <th style={thStyle}>Appeal ID</th>
                <th style={thStyle}>Case ID</th>
                <th style={thStyle}>Appeal Status</th>
                <th style={thStyle}>Submitted At</th>
              </tr>
            </thead>
            <tbody>
              {data.map((row, idx) => (
                <tr
                  key={row.appeal_id ?? idx}
                  style={idx % 2 === 1 ? { backgroundColor: "#f9fafb" } : undefined}
                >
                  <td style={tdStyle}>{row.appeal_id ?? "—"}</td>
                  <td style={tdStyle}>{row.case_id ?? "—"}</td>
                  <td style={tdStyle}>{row.appeal_status ?? "—"}</td>
                  <td style={tdStyle}>{formatDateTime(row.submitted_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}

// ─── AuditPage ───────────────────────────────────────────────────────────────

/**
 * AuditPage — fetches all three audit report endpoints in parallel via three
 * independent hooks (each fires its own useEffect on mount simultaneously).
 *
 * A single shared Spinner is displayed while ANY of the three responses is
 * still loading. All three tables are rendered once all data has resolved.
 *
 * Requirements: 20.4, 20.5
 */
export function AuditPage() {
  const { data: conflicts, loading: l1, error: e1 } = useConflictReassignments();
  const { data: postDecision, loading: l2, error: e2 } = usePostDecisionEvidence();
  const { data: appealsNoReview, loading: l3, error: e3 } = useAppealsWithoutIndependentReview();

  const loading = l1 || l2 || l3;

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "0.75rem",
          padding: "3rem",
          color: "#6b7280",
          fontSize: "0.95rem",
        }}
        role="status"
        aria-live="polite"
      >
        <Spinner />
        <span>Loading audit reports…</span>
      </div>
    );
  }

  return (
    <div style={{ padding: "1.5rem", maxWidth: "1200px", margin: "0 auto" }}>
      <h1 style={{ fontSize: "1.75rem", fontWeight: 600, marginBottom: "1.75rem", color: "#111827" }}>
        Audit Reports
      </h1>

      <ConflictReassignmentsTable data={conflicts?.data ?? []} error={e1} />
      <PostDecisionEvidenceTable data={postDecision?.data ?? []} error={e2} />
      <AppealsWithoutIndependentReviewTable data={appealsNoReview?.data ?? []} error={e3} />
    </div>
  );
}

export default AuditPage;
