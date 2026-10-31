import { get } from "./client";

/**
 * Fetch analytics summary statistics.
 * @returns {Promise<any>}
 */
export function fetchSummary() {
  return get("/analytics/summary");
}

/**
 * Fetch case counts over time.
 * @param {object} params - Query params (e.g. date range)
 * @returns {Promise<any>}
 */
export function fetchCasesOverTime(params = {}) {
  return get("/analytics/cases-over-time", params);
}

/**
 * Fetch outcome breakdown by program.
 * @returns {Promise<any>}
 */
export function fetchOutcomesByProgram() {
  return get("/analytics/outcomes-by-program");
}

/**
 * Fetch top assessments by flagged submission count.
 * @returns {Promise<any>}
 */
export function fetchTopAssessments() {
  return get("/analytics/top-assessments");
}

/**
 * Fetch similarity score distribution data.
 * @returns {Promise<any>}
 */
export function fetchSimilarityDistribution() {
  return get("/analytics/similarity-distribution");
}
