import React from "react";

const containerStyle = {
  display: "flex",
  alignItems: "center",
  gap: "0.75rem",
  fontSize: "0.9rem",
  userSelect: "none",
};

function btnStyle(disabled) {
  return {
    padding: "0.35rem 0.75rem",
    borderRadius: "4px",
    border: "1px solid #ccc",
    backgroundColor: disabled ? "#f5f5f5" : "#fff",
    color: disabled ? "#aaa" : "#1976d2",
    cursor: disabled ? "not-allowed" : "pointer",
    fontWeight: 500,
  };
}

/**
 * Pagination — reusable paginator.
 *
 * Props:
 *   totalCount  {number}   — total number of items
 *   page        {number}   — current 1-based page number
 *   pageSize    {number}   — items per page
 *   onPageChange {function} — called with the new page number
 */
export function Pagination({ totalCount, page, pageSize, onPageChange }) {
  const totalPages = Math.ceil(totalCount / pageSize) || 1;
  const isFirst = page <= 1;
  const isLast = page >= totalPages;

  function handlePrev() {
    if (!isFirst) onPageChange(page - 1);
  }

  function handleNext() {
    if (!isLast) onPageChange(page + 1);
  }

  return (
    <nav aria-label="Pagination" style={containerStyle}>
      <button
        onClick={handlePrev}
        disabled={isFirst}
        aria-disabled={isFirst}
        aria-label="Previous page"
        style={btnStyle(isFirst)}
      >
        ← Prev
      </button>

      <span aria-live="polite" aria-atomic="true">
        Page {page} of {totalPages}
      </span>

      <button
        onClick={handleNext}
        disabled={isLast}
        aria-disabled={isLast}
        aria-label="Next page"
        style={btnStyle(isLast)}
      >
        Next →
      </button>
    </nav>
  );
}

export default Pagination;
