import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useCases } from "../hooks/useCases";
import { Spinner } from "../components/Spinner";
import { ErrorMessage } from "../components/ErrorMessage";
import { Pagination } from "../components/Pagination";
import { Badge } from "../components/Badge";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const CASE_STATUSES = ["", "OPEN", "UNDER_REVIEW", "AWAITING_INFORMATION", "DECIDED", "APPEAL_PENDING", "CLOSED"];
const PRIORITIES = ["", "LOW", "MEDIUM", "HIGH"];
const PAGE_SIZE = 20;

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
  gap: "1rem",
  marginBottom: "1rem",
  fontSize: "0.9rem",
  color: "#424242",
  flexWrap: "wrap",
};

const labelStyle = {
  display: "flex",
  alignItems: "center",
  gap: "0.4rem",
};

const selectStyle = {
  padding: "0.35rem 0.6rem",
  borderRadius: "4px",
  border: "1px solid #ccc",
  fontSize: "0.875rem",
  color: "#212121",
  backgroundColor: "#fff",
  cursor: "pointer",
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

const rowStyle = {
  cursor: "pointer",
};

const rowHoverStyle = {
  backgroundColor: "#f9fafb",
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
// CaseFilters
// ---------------------------------------------------------------------------

/**
 * CaseFilters — dropdown controls for filtering the cases list.
 *
 * Props:
 *   status         {string}   — current status filter value
 *   priority       {string}   — current priority filter value
 *   onStatusChange  {function} — called with the new status string
 *   onPriorityChange {function} — called with the new priority string
 */
function CaseFilters({ status, priority, onStatusChange, onPriorityChange }) {
  return (
    <div style={filterBarStyle} role="search" aria-label="Case filters">
      <label style={labelStyle} htmlFor="status-filter">
        Status:
        <select
          id="status-filter"
          value={status}
          style={selectStyle}
          onChange={(e) => onStatusChange(e.target.value)}
          aria-label="Filter by status"
        >
          {CASE_STATUSES.map((s) => (
            <option key={s} value={s}>
              {s === "" ? "All statuses" : s.replace(/_/g, " ")}
            </option>
          ))}
        </select>
      </label>

      <label style={labelStyle} htmlFor="priority-filter">
        Priority:
        <select
          id="priority-filter"
          value={priority}
          style={selectStyle}
          onChange={(e) => onPriorityChange(e.target.value)}
          aria-label="Filter by priority"
        >
          {PRIORITIES.map((p) => (
            <option key={p} value={p}>
              {p === "" ? "All priorities" : p}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}

// ---------------------------------------------------------------------------
// CaseTable
// ---------------------------------------------------------------------------

/**
 * CaseTable — paginated table of integrity case records.
 *
 * Props:
 *   items    {Array}    — array of case objects
 *   onRowClick {function} — called with case_id when a row is clicked
 */
function CaseTable({ items, onRowClick }) {
  const [hoveredRow, setHoveredRow] = useState(null);

  if (!items || items.length === 0) {
    return <p style={emptyStyle}>No cases found.</p>;
  }

  return (
    <div style={tableContainerStyle}>
      <table style={tableStyle} aria-label="Integrity cases table">
        <thead>
          <tr>
            <th style={thStyle} scope="col">Case ID</th>
            <th style={thStyle} scope="col">Status</th>
            <th style={thStyle} scope="col">Priority</th>
            <th style={thStyle} scope="col">Opened</th>
            <th style={thStyle} scope="col">Conflict</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr
              key={item.case_id}
              onClick={() => onRowClick(item.case_id)}
              onMouseEnter={() => setHoveredRow(item.case_id)}
              onMouseLeave={() => setHoveredRow(null)}
              style={{
                ...rowStyle,
                ...(hoveredRow === item.case_id ? rowHoverStyle : {}),
              }}
              tabIndex={0}
              aria-label={`Case ${item.case_id}, status ${item.case_status}, priority ${item.priority}`}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onRowClick(item.case_id);
                }
              }}
            >
              <td style={tdStyle}>{item.case_id}</td>
              <td style={tdStyle}>{item.case_status.replace(/_/g, " ")}</td>
              <td style={tdStyle}>{item.priority}</td>
              <td style={tdStyle}>
                {new Date(item.opened_at).toLocaleDateString(undefined, {
                  year: "numeric",
                  month: "short",
                  day: "numeric",
                })}
              </td>
              <td style={tdStyle}>
                {item.has_conflict ? <Badge label="CONFLICT" variant="danger" /> : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// CasesPage
// ---------------------------------------------------------------------------

/**
 * CasesPage — lists all integrity cases with filtering and pagination.
 *
 * Requirements: 16.1, 16.3, 16.4, 16.5
 */
export function CasesPage() {
  const navigate = useNavigate();
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [page, setPage] = useState(1);

  const filters = {};
  if (status) filters.status = status;
  if (priority) filters.priority = priority;

  const { data, loading, error } = useCases(filters, page, PAGE_SIZE);

  function handleStatusChange(value) {
    setStatus(value);
    setPage(1); // reset to first page on filter change
  }

  function handlePriorityChange(value) {
    setPriority(value);
    setPage(1); // reset to first page on filter change
  }

  function handleRowClick(caseId) {
    navigate(`/cases/${caseId}`);
  }

  return (
    <main style={pageStyle} aria-label="Integrity Cases">
      <h1 style={headingStyle}>Integrity Cases</h1>

      <CaseFilters
        status={status}
        priority={priority}
        onStatusChange={handleStatusChange}
        onPriorityChange={handlePriorityChange}
      />

      {loading && (
        <div style={spinnerWrapStyle}>
          <Spinner />
          <span>Loading cases…</span>
        </div>
      )}

      {error && <ErrorMessage error={error} />}

      {data && (
        <>
          <CaseTable items={data.items} onRowClick={handleRowClick} />
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

export default CasesPage;
