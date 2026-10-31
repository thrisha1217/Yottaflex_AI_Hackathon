import { get, patch } from "./client";

/**
 * Fetch a paginated list of cases.
 * @param {object} params - Query params: status, priority, assigned_reviewer_id, page, page_size
 * @returns {Promise<any>}
 */
export function fetchCases(params = {}) {
  return get("/cases", params);
}

/**
 * Fetch a single case by ID.
 * @param {string|number} id
 * @returns {Promise<any>}
 */
export function fetchCase(id) {
  return get(`/cases/${id}`);
}

/**
 * Update the status of a case.
 * @param {string|number} id - Case ID
 * @param {object} body - Request body (e.g. { status })
 * @returns {Promise<any>}
 */
export function patchCaseStatus(id, body) {
  return patch(`/cases/${id}/status`, body);
}
