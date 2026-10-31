import { get } from "./client";

/**
 * Fetch a paginated list of submissions.
 * @param {object} params - Query params: flagged, page, page_size
 * @returns {Promise<any>}
 */
export function fetchSubmissions(params = {}) {
  return get("/submissions", params);
}

/**
 * Fetch a single submission by ID.
 * @param {string|number} id
 * @returns {Promise<any>}
 */
export function fetchSubmission(id) {
  return get(`/submissions/${id}`);
}

/**
 * Fetch the similarity report for a submission.
 * @param {string|number} id - Similarity report ID
 * @returns {Promise<any>}
 */
export function fetchSimilarityReport(id) {
  return get(`/similarity-reports/${id}`);
}
