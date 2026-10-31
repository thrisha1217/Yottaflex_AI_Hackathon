import React, { useState } from "react";
import { useSubmissions } from "../hooks/useSubmissions";
import { Spinner } from "../components/Spinner";
import { ErrorMessage } from "../components/ErrorMessage";
import { Pagination } from "../components/Pagination";
import { Badge } from "../components/Badge";

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const pageStyle = {
  padding: "1.5rem 2rem",
  fontFamily: "system-ui, sans-serif",
  color: "#212121",
};

const headingStyle = {
  fontSize: "1.5rem",
  fontWeight: 700,
  marginBottom: "1rem",
};

const filterBarStyle = {
  display: "flex",
  alignItems: "center",
  gap: "0.5rem",
  marginBottom: "1rem",
  fontSize: "0.9rem",
  color: "#424242",
};

const checkboxStyle = {
  cursor: "pointer",
  accentColor: "#1976d2",
  width: "1rem",
  height: "1rem",
};

const tableContainerStyle = {
  overflowX: "auto",
  marginBottom: "1rem",
};

const tableStyle = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: "0.875rem",
};

const thStyle = {
  padding: "0.65rem 0.75rem",
  textAlign: "left",
  backgroundColor: "#f5f5f5",
  borderBottom: "2px solid #e0e0e0",
  fontWeight: 600,
  color: "#424242",
  whiteSpace: "nowrap",
};

const tdStyle = {
  padding: "0.6rem 0.75rem",
  borderBottom: "1px solid #eeeeee",
  verticalAlign: "middle",
};

const emptyStyle = {
  padding: "2rem",
  textAlign: "center",
  color: "#9e9e9e",
  fontSize: "0.9rem",
};

const spinnerWrapStyle = {
  display: "flex",
  alignItems: "center",
  gap: "0.5rem",
  margin: "1rem 0",
  fontSize: "0.9rem",
  color: "#757575",
};

// ---------------------------------------------------------------------------
// SubmissionFilters
// ---------------------------------------------------------------------------

/**
 * SubmissionFilters — filter controls for the submissions list.
 *
 * Props:
 *   flagged       {boolean}  — current state of the "flagged only" toggle
 *   onFlaggedChange {function} — called with the new boolean value
 */
function SubmissionFilters({ flagged, onFlaggedChange }) {
  return (
    <div style={filterBarStyle} role="search" aria-label="Submission filters">
      <label
        style={{ display: "flex", alignItems: "center", gap: "0.4rem", cursor: "pointer" }}
        htmlFor="flagged-filter"
      >
        <input
          id="flagged-filter"
          type="checkbox"
          checked={flagged}
          style={checkboxStyle}
          onChange={(e) => onFlaggedChange(e.target.checked)}
          aria-label="Show flagged submissions only"
        />
        Show flagged only
      </label>
    </div>
  );
}

// ---------------------------------------------------------------------------
// SubmissionTable
// ---------------------------------------------------------------------------

/**
 * SubmissionTable — paginated table of submission records.
 *
 * Props:
 *   items {Array} — array of submission objects
 */
function SubmissionTable({ items }) {
  if (!items || items.length === 0) {
    return <p style={emptyStyle}>No submissions found.</p>;
  }

  return (
    <div style={tableContainerStyle}>
      <table style={tableStyle} aria-label="Submissions table">
        <thead>
          <tr>
            <th style={thStyle} scope="col">ID</th>
            <th style={thStyle} scope="col">Learner</th>
            <th style={thStyle} scope="col">Assessment</th>
            <th style={thStyle} scope="col">Submitted</th>
            <th style={thStyle} scope="col">Score</th>
            <th style={thStyle} scope="col">Status</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.submission_id}>
              <td style={tdStyle}>{item.submission_id}</td>
              <td style={tdStyle}>{item.learner_id}</td>
              <td style={tdStyle}>{item.assessment_id}</td>
              <td style={tdStyle}>
                {new Date(item.submitted_at).toLocaleDateString(undefined, {
                  year: "numeric",
                  month: "short",
                  day: "numeric",
                })}
              </td>
              <td style={tdStyle}>
                {item.similarity_score != null ? `${item.similarity_score}%` : "—"}
              </td>
              <td style={tdStyle}>
                {item.review_required ? (
                  <Badge label="Flagged" variant="danger" />
                ) : (
                  <Badge label="Clear" variant="success" />
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// SubmissionsPage
// ---------------------------------------------------------------------------

const PAGE_SIZE = 20;

/**
 * SubmissionsPage — lists all submissions with filtering and pagination.
 *
 * Requirements: 15.1, 16.4
 */
export function SubmissionsPage() {
  const [flagged, setFlagged] = useState(false);
  const [page, setPage] = useState(1);

  const filters = flagged ? { flagged: true } : {};
  const { data, loading, error } = useSubmissions(filters, page, PAGE_SIZE);

  function handleFlaggedChange(value) {
    setFlagged(value);
    setPage(1); // reset to first page whenever the filter changes
  }

  return (
    <main style={pageStyle} aria-label="Submissions">
      <h1 style={headingStyle}>Submissions</h1>

      <SubmissionFilters flagged={flagged} onFlaggedChange={handleFlaggedChange} />

      {loading && (
        <div style={spinnerWrapStyle}>
          <Spinner />
          <span>Loading submissions…</span>
        </div>
      )}

      {error && <ErrorMessage error={error} />}

      {data && (
        <>
          <SubmissionTable items={data.items} />
          <Pagination
            totalCount={data.total_count}
            page={page}
            pageSize={PAGE_SIZE}
            onPageChange={setPage}
          />
        </>
      )}
    </main>
  );
}

export default SubmissionsPage;
