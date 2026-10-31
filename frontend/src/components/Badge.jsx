import React from "react";

/** Colour map for each variant */
const VARIANT_STYLES = {
  default: {
    backgroundColor: "#e0e0e0",
    color: "#424242",
    border: "1px solid #bdbdbd",
  },
  success: {
    backgroundColor: "#e8f5e9",
    color: "#2e7d32",
    border: "1px solid #a5d6a7",
  },
  warning: {
    backgroundColor: "#fff3e0",
    color: "#e65100",
    border: "1px solid #ffcc80",
  },
  danger: {
    backgroundColor: "#ffebee",
    color: "#c62828",
    border: "1px solid #ef9a9a",
  },
  info: {
    backgroundColor: "#e3f2fd",
    color: "#1565c0",
    border: "1px solid #90caf9",
  },
};

const baseStyle = {
  display: "inline-block",
  padding: "0.2rem 0.55rem",
  borderRadius: "12px",
  fontSize: "0.78rem",
  fontWeight: 600,
  lineHeight: 1.4,
  whiteSpace: "nowrap",
  verticalAlign: "middle",
};

/**
 * Badge — status / conflict badge with colour coding.
 *
 * Props:
 *   label   {string}  — text to display
 *   variant {string}  — "default" | "success" | "warning" | "danger" | "info"
 */
export function Badge({ label, variant = "default" }) {
  const variantStyle = VARIANT_STYLES[variant] ?? VARIANT_STYLES.default;

  return (
    <span style={{ ...baseStyle, ...variantStyle }}>
      {label}
    </span>
  );
}

export default Badge;
