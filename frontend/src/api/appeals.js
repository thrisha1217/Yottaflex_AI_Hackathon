import { get, post } from "./client";

/**
 * Fetch all appeals for a case.
 * @param {string|number} caseId
 * @returns {Promise<any>}
 */
export function fetchAppeals(caseId) {
  return get(`/cases/${caseId}/appeals`);
}

/**
 * Submit a new appeal for a case.
 * @param {string|number} caseId
 * @param {object} body - Appeal payload
 * @returns {Promise<any>}
 */
export function postAppeal(caseId, body) {
  return post(`/cases/${caseId}/appeals`, body);
}

/**
 * Submit a review for an appeal.
 * @param {string|number} id - Appeal ID
 * @param {object} body - Review payload
 * @returns {Promise<any>}
 */
export function postAppealReview(id, body) {
  return post(`/appeals/${id}/reviews`, body);
}
