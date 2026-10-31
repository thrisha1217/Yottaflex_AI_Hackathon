import React from "react";

const containerStyle = {
  display: "flex",
  alignItems: "flex-start",
  gap: "0.5rem",
  padding: "0.75rem 1rem",
  borderRadius: "4px",
  border: "1px solid #f5c2c7",
  backgroundColor: "#fff3f3",
  color: "#b91c1c",
  fontSize: "0.9rem",
  lineHeight: "1.4",
};

const iconStyle = {
  flexShrink: 0,
  fontStyle: "normal",
  fontSize: "1rem",
};

/**
 * ErrorMessage — renders a non-crashing inline error.
 *
 * Accepts:
 *   error — string | Error | null | undefined
 *
 * Renders nothing when error is falsy.
 * Extracts the `detail` field if the error has one (API error shape),
 * falls back to `error.message`, then to the raw string value.
 */
export function ErrorMessage({ error }) {
  if (!error) return null;

  let message;
  if (typeof error === "string") {
    message = error;
  } else if (error && typeof error === "object") {
    // API error objects may carry a `detail` field
    message = error.detail || error.message || String(error);
  } else {
    message = String(error);
  }

  return (
    <div role="alert" aria-live="assertive" style={containerStyle}>
      <span aria-hidden="true" style={iconStyle}>⚠️</span>
      <span>{message}</span>
    </div>
  );
}

export default ErrorMessage;
