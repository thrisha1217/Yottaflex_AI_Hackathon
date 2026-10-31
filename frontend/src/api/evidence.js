import { get, post } from "./client";

/**
 * Fetch all evidence items for a case.
 * @param {string|number} caseId
 * @returns {Promise<any>}
 */
export function fetchEvidence(caseId) {
  return get(`/cases/${caseId}/evidence`);
}

/**
 * Submit a new evidence item to a case.
 * @param {string|number} caseId
 * @param {object} body - Evidence payload
 * @returns {Promise<any>}
 */
export function postEvidence(caseId, body) {
  return post(`/cases/${caseId}/evidence`, body);
}
