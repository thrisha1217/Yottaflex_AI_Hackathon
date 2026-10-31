import React from "react";

const spinnerStyle = {
  display: "inline-block",
  width: "1.5rem",
  height: "1.5rem",
  border: "3px solid #e0e0e0",
  borderTopColor: "#1976d2",
  borderRadius: "50%",
  animation: "spin 0.7s linear infinite",
};

const keyframesStyle = `
@keyframes spin {
  to { transform: rotate(360deg); }
}
`;

/**
 * Spinner — accessible loading indicator.
 * Injects a minimal @keyframes rule once into the document <head>.
 */
export function Spinner() {
  // Inject keyframes once per page load
  if (typeof document !== "undefined" && !document.getElementById("__spinner-kf__")) {
    const style = document.createElement("style");
    style.id = "__spinner-kf__";
    style.textContent = keyframesStyle;
    document.head.appendChild(style);
  }

  return (
    <span
      role="status"
      aria-label="Loading"
      style={spinnerStyle}
    />
  );
}

export default Spinner;
