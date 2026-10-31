import { get, post } from "./client";

/**
 * Fetch all decisions for a case.
 * @param {string|number} caseId
 * @returns {Promise<any>}
 */
export function fetchDecisions(caseId) {
  return get(`/cases/${caseId}/decisions`);
}

/**
 * Submit a new decision for a case.
 * @param {string|number} caseId
 * @param {object} body - Decision payload
 * @returns {Promise<any>}
 */
export function postDecision(caseId, body) {
  return post(`/cases/${caseId}/decisions`, body);
}
