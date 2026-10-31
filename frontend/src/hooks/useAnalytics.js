import { useState, useEffect } from "react";
import {
  fetchSummary,
  fetchCasesOverTime,
  fetchOutcomesByProgram,
  fetchTopAssessments,
  fetchSimilarityDistribution,
} from "../api/analytics";

/**
 * Generic single-fetch hook factory (internal helper).
 * Calls fetchFn() on mount and whenever depsKey changes.
 */
function useFetch(fetchFn, depsKey) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchFn()
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [depsKey]);

  return { data, loading, error };
}

/**
 * Fetch high-level analytics summary statistics.
 *
 * @returns {{ data: any, loading: boolean, error: any }}
 */
export function useSummary() {
  return useFetch(fetchSummary, "summary");
}

/**
 * Fetch case counts grouped over time.
 *
 * @param {object} params - Query params (e.g. date range filters)
 * @returns {{ data: any, loading: boolean, error: any }}
 */
export function useCasesOverTime(params = {}) {
  const paramsKey = JSON.stringify(params);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchCasesOverTime(params)
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paramsKey]);

  return { data, loading, error };
}

/**
 * Fetch outcome breakdown by academic program.
 *
 * @returns {{ data: any, loading: boolean, error: any }}
 */
export function useOutcomesByProgram() {
  return useFetch(fetchOutcomesByProgram, "outcomes-by-program");
}

/**
 * Fetch top assessments ranked by flagged submission count.
 *
 * @returns {{ data: any, loading: boolean, error: any }}
 */
export function useTopAssessments() {
  return useFetch(fetchTopAssessments, "top-assessments");
}

/**
 * Fetch similarity score distribution data.
 *
 * @returns {{ data: any, loading: boolean, error: any }}
 */
export function useSimilarityDistribution() {
  return useFetch(fetchSimilarityDistribution, "similarity-distribution");
}
