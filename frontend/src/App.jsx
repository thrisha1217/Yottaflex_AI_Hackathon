import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { DashboardPage } from "./pages/DashboardPage";
import { SubmissionsPage } from "./pages/SubmissionsPage";
import { CasesPage } from "./pages/CasesPage";
import { CaseDetailPage } from "./pages/CaseDetailPage";
import { AnalyticsPage } from "./pages/AnalyticsPage";
import { AuditPage } from "./pages/AuditPage";

// ─── Nav styles ──────────────────────────────────────────────────────────────

const navStyle = {
  display: "flex",
  gap: "0",
  alignItems: "center",
  backgroundColor: "#1976d2",
  padding: "0 1.5rem",
  boxShadow: "0 2px 4px rgba(0,0,0,0.15)",
};

const brandStyle = {
  color: "#fff",
  fontWeight: 700,
  fontSize: "1rem",
  padding: "0.9rem 1rem 0.9rem 0",
  marginRight: "1.5rem",
  textDecoration: "none",
  letterSpacing: "0.02em",
  flexShrink: 0,
};

const navLinkStyle = {
  color: "rgba(255,255,255,0.82)",
  textDecoration: "none",
  padding: "0.9rem 0.85rem",
  fontSize: "0.875rem",
  fontWeight: 500,
  borderBottom: "3px solid transparent",
  transition: "color 0.15s, border-color 0.15s",
};

const navLinkActiveStyle = {
  color: "#fff",
  borderBottom: "3px solid #fff",
};

function NavBar() {
  const links = [
    { to: "/", label: "Dashboard", end: true },
    { to: "/submissions", label: "Submissions" },
    { to: "/cases", label: "Cases" },
    { to: "/analytics", label: "Analytics" },
    { to: "/audit", label: "Audit" },
  ];

  return (
    <nav style={navStyle} aria-label="Main navigation">
      <span style={brandStyle}>Academic Integrity</span>
      {links.map(({ to, label, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          style={({ isActive }) => ({
            ...navLinkStyle,
            ...(isActive ? navLinkActiveStyle : {}),
          })}
        >
          {label}
        </NavLink>
      ))}
    </nav>
  );
}

// ─── App ─────────────────────────────────────────────────────────────────────

/**
 * App — root component.
 *
 * Sets up BrowserRouter with React Router v6 Routes, wraps all pages in
 * ErrorBoundary, and renders the navigation bar.
 *
 * Routes:
 *   /                  → DashboardPage
 *   /submissions        → SubmissionsPage
 *   /cases             → CasesPage
 *   /cases/:caseId     → CaseDetailPage
 *   /analytics         → AnalyticsPage
 *   /audit             → AuditPage
 *
 * Requirements: 15.4, 16.1, 18.5, 20.4
 */
function App() {
  return (
    <BrowserRouter>
      <NavBar />
      <ErrorBoundary>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/submissions" element={<SubmissionsPage />} />
          <Route path="/cases" element={<CasesPage />} />
          <Route path="/cases/:caseId" element={<CaseDetailPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/audit" element={<AuditPage />} />
        </Routes>
      </ErrorBoundary>
    </BrowserRouter>
  );
}

export default App;
