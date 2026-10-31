import { get } from "./client";

/**
 * Fetch cases where a conflict of interest triggered a reviewer reassignment.
 * @returns {Promise<any>}
 */
export function fetchConflictReassignments() {
  return get("/audit/conflict-reassignments");
}

/**
 * Fetch evidence submitted after a decision was recorded.
 * @returns {Promise<any>}
 */
export function fetchPostDecisionEvidence() {
  return get("/audit/post-decision-evidence");
}

/**
 * Fetch appeals that lack an independent reviewer review.
 * @returns {Promise<any>}
 */
export function fetchAppealsWithoutIndependentReview() {
  return get("/audit/appeals-without-independent-review");
}

/**
 * Fetch the audit log with optional filters.
 * @param {object} params - Query params (e.g. entity_type, entity_id, page, page_size)
 * @returns {Promise<any>}
 */
export function fetchAuditLog(params = {}) {
  return get("/audit-log", params);
}
