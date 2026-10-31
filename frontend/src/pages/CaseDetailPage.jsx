import React from "react";
import { useParams } from "react-router-dom";
import { useCase } from "../hooks/useCase";
import { Spinner } from "../components/Spinner";
import { ErrorMessage } from "../components/ErrorMessage";
import { Badge } from "../components/Badge";

// ─── Shared styles ────────────────────────────────────────────────────────────

const sectionStyle = {
  marginBottom: "1.5rem",
  padding: "1.25rem 1.5rem",
  border: "1px solid #e0e0e0",
  borderRadius: "8px",
  backgroundColor: "#fff",
  boxShadow: "0 1px 3px rgba(0,0,0,0.07)",
};

const sectionTitleStyle = {
  margin: "0 0 1rem 0",
  fontSize: "1rem",
  fontWeight: 700,
  color: "#333",
  textTransform: "uppercase",
  letterSpacing: "0.04em",
  borderBottom: "1px solid #f0f0f0",
  paddingBottom: "0.5rem",
};

const fieldRowStyle = {
  display: "flex",
  gap: "0.4rem",
  alignItems: "center",
  marginBottom: "0.4rem",
  fontSize: "0.9rem",
};

const labelStyle = {
  fontWeight: 600,
  color: "#555",
  minWidth: "130px",
};

const tableStyle = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: "0.875rem",
};

const thStyle = {
  textAlign: "left",
  padding: "0.5rem 0.75rem",
  backgroundColor: "#f5f5f5",
  borderBottom: "2px solid #e0e0e0",
  fontWeight: 700,
  color: "#444",
  fontSize: "0.8rem",
  textTransform: "uppercase",
  letterSpacing: "0.03em",
};

const tdStyle = {
  padding: "0.5rem 0.75rem",
  borderBottom: "1px solid #f0f0f0",
  verticalAlign: "top",
};

const emptyStyle = {
  color: "#999",
  fontStyle: "italic",
  fontSize: "0.875rem",
  padding: "0.5rem 0",
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatDate(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function caseStatusVariant(status) {
  switch (status) {
    case "OPEN":               return "info";
    case "UNDER_REVIEW":       return "warning";
    case "DECIDED":            return "success";
    case "CLOSED":             return "default";
    case "APPEAL_PENDING":     return "warning";
    case "AWAITING_INFORMATION": return "warning";
    default:                   return "default";
  }
}

function priorityVariant(priority) {
  switch (priority) {
    case "HIGH":   return "danger";
    case "MEDIUM": return "warning";
    case "LOW":    return "success";
    default:       return "default";
  }
}

function reportStatusVariant(status) {
  switch (status) {
    case "FLAGGED":   return "danger";
    case "CLEARED":   return "success";
    case "PENDING":   return "warning";
    default:          return "default";
  }
}

function conflictVariant(status) {
  switch (status) {
    case "CONFLICT":   return "danger";
    case "NO_CONFLICT": return "success";
    default:           return "default";
  }
}

function outcomeVariant(outcome) {
  switch (outcome) {
    case "UPHELD":     return "success";
    case "OVERTURNED": return "warning";
    case "DISMISSED":  return "danger";
    case "NO_BREACH":  return "success";
    case "BREACH":     return "danger";
    default:           return "default";
  }
}

function appealStatusVariant(status) {
  switch (status) {
    case "PENDING":    return "warning";
    case "UPHELD":     return "success";
    case "OVERTURNED": return "warning";
    case "DISMISSED":  return "danger";
    case "WITHDRAWN":  return "default";
    default:           return "default";
  }
}

// ─── CaseHeader ──────────────────────────────────────────────────────────────

/**
 * CaseHeader — displays case_id, case_status, priority, and dates.
 * Validates: Requirements 16.2
 */
function CaseHeader({ caseData }) {
  return (
    <section style={sectionStyle} aria-label="Case Header">
      <h2 style={{ ...sectionTitleStyle, marginBottom: "0.75rem" }}>Case</h2>
      <div style={{ display: "flex", gap: "2rem", flexWrap: "wrap" }}>
        <div>
          <div style={fieldRowStyle}>
            <span style={labelStyle}>Case ID</span>
            <code style={{ fontFamily: "monospace", fontSize: "0.9rem" }}>
              {caseData.case_id}
            </code>
          </div>
          <div style={fieldRowStyle}>
            <span style={labelStyle}>Status</span>
            <Badge
              label={caseData.case_status}
              variant={caseStatusVariant(caseData.case_status)}
            />
          </div>
          <div style={fieldRowStyle}>
            <span style={labelStyle}>Priority</span>
            <Badge
              label={caseData.priority}
              variant={priorityVariant(caseData.priority)}
            />
          </div>
        </div>
        <div>
          <div style={fieldRowStyle}>
            <span style={labelStyle}>Opened</span>
            <span>{formatDate(caseData.opened_at)}</span>
          </div>
          {caseData.closed_at && (
            <div style={fieldRowStyle}>
              <span style={labelStyle}>Closed</span>
              <span>{formatDate(caseData.closed_at)}</span>
            </div>
          )}
          {caseData.has_conflict && (
            <div style={fieldRowStyle}>
              <Badge label="Conflict Present" variant="danger" />
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

// ─── SimilarityReportCard ─────────────────────────────────────────────────────

/**
 * SimilarityReportCard — similarity score, review_required flag, report_status.
 * Validates: Requirements 16.2
 */
function SimilarityReportCard({ report }) {
  if (!report) {
    return (
      <section style={sectionStyle} aria-label="Similarity Report">
        <h2 style={sectionTitleStyle}>Similarity Report</h2>
        <p style={emptyStyle}>No similarity report available.</p>
      </section>
    );
  }

  const scorePercent =
    typeof report.similarity_score === "number"
      ? `${(report.similarity_score * 100).toFixed(1)}%`
      : report.similarity_score ?? "—";

  return (
    <section style={sectionStyle} aria-label="Similarity Report">
      <h2 style={sectionTitleStyle}>Similarity Report</h2>
      <div style={fieldRowStyle}>
        <span style={labelStyle}>Score</span>
        <strong style={{ fontSize: "1.1rem" }}>{scorePercent}</strong>
      </div>
      <div style={fieldRowStyle}>
        <span style={labelStyle}>Status</span>
        <Badge
          label={report.report_status}
          variant={reportStatusVariant(report.report_status)}
        />
      </div>
      <div style={fieldRowStyle}>
        <span style={labelStyle}>Review Required</span>
        {report.review_required ? (
          <Badge label="Yes" variant="warning" />
        ) : (
          <Badge label="No" variant="success" />
        )}
      </div>
    </section>
  );
}

// ─── ReviewerList ─────────────────────────────────────────────────────────────

/**
 * ReviewerList — displays each reviewer's name, role, and conflict badge.
 * Validates: Requirements 16.2
 */
function ReviewerList({ reviewers }) {
  return (
    <section style={sectionStyle} aria-label="Reviewers">
      <h2 style={sectionTitleStyle}>Reviewers</h2>
      {reviewers.length === 0 ? (
        <p style={emptyStyle}>No reviewers assigned.</p>
      ) : (
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>Name / ID</th>
              <th style={thStyle}>Role</th>
              <th style={thStyle}>Conflict</th>
              <th style={thStyle}>Assigned</th>
            </tr>
          </thead>
          <tbody>
            {reviewers.map((r) => (
              <tr key={r.assignment_id ?? r.reviewer_id}>
                <td style={tdStyle}>
                  {r.reviewer_name ? (
                    <strong>{r.reviewer_name}</strong>
                  ) : (
                    <code style={{ fontFamily: "monospace", fontSize: "0.85rem" }}>
                      {r.reviewer_id}
                    </code>
                  )}
                </td>
                <td style={tdStyle}>{r.assignment_role}</td>
                <td style={tdStyle}>
                  <Badge
                    label={r.conflict_status}
                    variant={conflictVariant(r.conflict_status)}
                  />
                  {r.conflict_reason && (
                    <div style={{ fontSize: "0.8rem", color: "#666", marginTop: "0.2rem" }}>
                      {r.conflict_reason}
                    </div>
                  )}
                </td>
                <td style={tdStyle}>{formatDate(r.assigned_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

// ─── EvidenceList ─────────────────────────────────────────────────────────────

/**
 * EvidenceList — evidence items ordered by added_at ascending.
 * Validates: Requirements 16.6
 */
function EvidenceList({ evidence }) {
  const sorted = [...evidence].sort(
    (a, b) => new Date(a.added_at) - new Date(b.added_at)
  );

  return (
    <section style={sectionStyle} aria-label="Evidence">
      <h2 style={sectionTitleStyle}>Evidence</h2>
      {sorted.length === 0 ? (
        <p style={emptyStyle}>No evidence items recorded.</p>
      ) : (
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>ID</th>
              <th style={thStyle}>Type</th>
              <th style={thStyle}>Added By</th>
              <th style={thStyle}>Added At</th>
              <th style={thStyle}>Material</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((item) => (
              <tr key={item.evidence_id}>
                <td style={tdStyle}>
                  <code style={{ fontFamily: "monospace", fontSize: "0.82rem" }}>
                    {item.evidence_id}
                  </code>
                </td>
                <td style={tdStyle}>{item.evidence_type}</td>
                <td style={tdStyle}>{item.added_by_role}</td>
                <td style={tdStyle}>{formatDate(item.added_at)}</td>
                <td style={tdStyle}>
                  {item.is_material ? (
                    <Badge label="Material" variant="info" />
                  ) : (
                    <Badge label="Non-material" variant="default" />
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

// ─── DecisionCard ─────────────────────────────────────────────────────────────

/**
 * DecisionCard — decision outcome, rationale, decided_at.
 * Validates: Requirements 17.3
 */
function DecisionCard({ decisions }) {
  return (
    <section style={sectionStyle} aria-label="Decisions">
      <h2 style={sectionTitleStyle}>Decisions</h2>
      {decisions.length === 0 ? (
        <p style={emptyStyle}>No decisions recorded.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {decisions.map((d) => (
            <div
              key={d.decision_id}
              style={{
                padding: "1rem",
                border: "1px solid #e8e8e8",
                borderRadius: "6px",
                backgroundColor: "#fafafa",
              }}
            >
              <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", marginBottom: "0.5rem", alignItems: "center" }}>
                <Badge
                  label={d.decision_outcome}
                  variant={outcomeVariant(d.decision_outcome)}
                />
                {d.is_final && <Badge label="Final" variant="info" />}
                <span style={{ fontSize: "0.82rem", color: "#777" }}>
                  {formatDate(d.decided_at)}
                </span>
              </div>
              <p style={{ margin: 0, fontSize: "0.875rem", color: "#333", lineHeight: 1.5 }}>
                {d.rationale}
              </p>
              <div style={{ marginTop: "0.4rem", fontSize: "0.8rem", color: "#888" }}>
                Reviewer ID:{" "}
                <code style={{ fontFamily: "monospace" }}>{d.reviewer_id}</code>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

// ─── AppealList ───────────────────────────────────────────────────────────────

/**
 * AppealList — each appeal with status, submitted_at, independence_verified,
 * and resolved_at when UPHELD or OVERTURNED.
 * Validates: Requirements 17.4, 17.5
 */
function AppealList({ appeals }) {
  return (
    <section style={sectionStyle} aria-label="Appeals">
      <h2 style={sectionTitleStyle}>Appeals</h2>
      {appeals.length === 0 ? (
        <p style={emptyStyle}>No appeals filed.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {appeals.map((appeal) => {
            const showResolved =
              appeal.appeal_status === "UPHELD" ||
              appeal.appeal_status === "OVERTURNED";

            return (
              <div
                key={appeal.appeal_id}
                style={{
                  padding: "1rem",
                  border: "1px solid #e8e8e8",
                  borderRadius: "6px",
                  backgroundColor: "#fafafa",
                }}
              >
                {/* Header row */}
                <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", alignItems: "center", marginBottom: "0.5rem" }}>
                  <Badge
                    label={appeal.appeal_status}
                    variant={appealStatusVariant(appeal.appeal_status)}
                  />
                  <span style={{ fontSize: "0.82rem", color: "#777" }}>
                    Appeal #{appeal.appeal_no ?? appeal.appeal_id}
                  </span>
                </div>

                {/* Fields */}
                <div style={{ fontSize: "0.875rem", display: "flex", flexDirection: "column", gap: "0.3rem" }}>
                  <div style={fieldRowStyle}>
                    <span style={labelStyle}>Submitted</span>
                    <span>{formatDate(appeal.submitted_at)}</span>
                  </div>

                  {/* independence_verified — shown from AppealReview if present */}
                  {appeal.independence_verified !== undefined && (
                    <div style={fieldRowStyle}>
                      <span style={labelStyle}>Independence</span>
                      {appeal.independence_verified ? (
                        <Badge label="Verified" variant="success" />
                      ) : (
                        <Badge label="Not Verified" variant="danger" />
                      )}
                    </div>
                  )}

                  {/* AppealReview outcome if present */}
                  {appeal.review_outcome && (
                    <div style={fieldRowStyle}>
                      <span style={labelStyle}>Review Outcome</span>
                      <Badge
                        label={appeal.review_outcome}
                        variant={outcomeVariant(appeal.review_outcome)}
                      />
                    </div>
                  )}

                  {/* resolved_at only for UPHELD / OVERTURNED */}
                  {showResolved && appeal.resolved_at && (
                    <div style={fieldRowStyle}>
                      <span style={labelStyle}>Resolved</span>
                      <span>{formatDate(appeal.resolved_at)}</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

// ─── CaseEventTimeline ────────────────────────────────────────────────────────

/**
 * CaseEventTimeline — full event list ordered by occurred_at ascending.
 * Validates: Requirements 17.3
 */
function CaseEventTimeline({ events }) {
  const sorted = [...events].sort(
    (a, b) => new Date(a.occurred_at) - new Date(b.occurred_at)
  );

  return (
    <section style={sectionStyle} aria-label="Case Event Timeline">
      <h2 style={sectionTitleStyle}>Event Timeline</h2>
      {sorted.length === 0 ? (
        <p style={emptyStyle}>No events recorded.</p>
      ) : (
        <ol
          style={{
            margin: 0,
            padding: 0,
            listStyle: "none",
            position: "relative",
            paddingLeft: "1.5rem",
          }}
        >
          {/* Vertical line */}
          <li
            aria-hidden="true"
            style={{
              position: "absolute",
              left: "0.45rem",
              top: "0.6rem",
              bottom: "0.6rem",
              width: "2px",
              backgroundColor: "#e0e0e0",
              pointerEvents: "none",
            }}
          />
          {sorted.map((ev, idx) => (
            <li
              key={ev.event_id ?? idx}
              style={{
                position: "relative",
                marginBottom: "0.85rem",
                paddingLeft: "0.75rem",
              }}
            >
              {/* Timeline dot */}
              <span
                aria-hidden="true"
                style={{
                  position: "absolute",
                  left: "-1.05rem",
                  top: "0.3rem",
                  width: "0.6rem",
                  height: "0.6rem",
                  borderRadius: "50%",
                  backgroundColor: "#1976d2",
                  border: "2px solid #fff",
                  boxShadow: "0 0 0 1px #1976d2",
                }}
              />
              <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", alignItems: "center" }}>
                <span
                  style={{
                    fontSize: "0.82rem",
                    fontWeight: 700,
                    color: "#333",
                    whiteSpace: "nowrap",
                  }}
                >
                  {ev.event_type}
                </span>
                <span style={{ fontSize: "0.8rem", color: "#888" }}>
                  {formatDate(ev.occurred_at)}
                </span>
                <Badge label={ev.actor_role} variant="info" />
                {ev.previous_status && ev.new_status && (
                  <span style={{ fontSize: "0.8rem", color: "#555" }}>
                    {ev.previous_status} → {ev.new_status}
                  </span>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

// ─── CaseDetailPage ───────────────────────────────────────────────────────────

/**
 * CaseDetailPage — full case detail view.
 *
 * Renders:
 *   - CaseHeader          (case_id, case_status, priority)
 *   - SimilarityReportCard (score, review_required, report_status)
 *   - ReviewerList         (reviewer name, role, conflict badge)
 *   - EvidenceList         (ordered by added_at asc)
 *   - DecisionCard         (outcome, rationale, decided_at)
 *   - AppealList           (status, independence_verified, resolved_at for UPHELD/OVERTURNED)
 *   - CaseEventTimeline    (full event list ordered by occurred_at asc)
 *
 * Validates: Requirements 16.2, 16.6, 17.3, 17.4, 17.5
 */
export function CaseDetailPage() {
  const { caseId } = useParams();
  const { caseData, evidence, decisions, appeals, loading, error } = useCase(caseId);

  if (loading) return <Spinner />;
  if (error) return <ErrorMessage error={error} />;
  if (!caseData) return null;

  return (
    <div style={{ padding: "1.5rem", maxWidth: "1000px", margin: "0 auto" }}>
      <h1 style={{ marginBottom: "1.5rem", fontSize: "1.75rem", fontWeight: 700, color: "#1a1a1a" }}>
        Case Detail
      </h1>

      {/* Requirements 16.2 */}
      <CaseHeader caseData={caseData} />

      {/* Requirements 16.2 */}
      <SimilarityReportCard report={caseData.report_summary} />

      {/* Requirements 16.2 */}
      <ReviewerList reviewers={caseData.reviewers || []} />

      {/* Requirements 16.6 */}
      <EvidenceList evidence={evidence || []} />

      {/* Requirements 17.3 */}
      <DecisionCard decisions={decisions || []} />

      {/* Requirements 17.4, 17.5 */}
      <AppealList appeals={appeals || []} />

      {/* Requirements 17.3 */}
      <CaseEventTimeline events={caseData.events || []} />
    </div>
  );
}

export default CaseDetailPage;
