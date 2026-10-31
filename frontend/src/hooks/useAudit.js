import { useState, useEffect } from "react";
import {
  fetchConflictReassignments,
  fetchPostDecisionEvidence,
  fetchAppealsWithoutIndependentReview,
} from "../api/audit";

/**
 * Generic single-fetch hook factory (internal helper).
 * Calls fetchFn() on mount; re-fetches whenever cacheKey changes.
 */
function useFetch(fetchFn, cacheKey) {
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
  }, [cacheKey]);

  return { data, loading, error };
}

/**
 * Fetch cases where a conflict of interest triggered a reviewer reassignment.
 *
 * @returns {{ data: any, loading: boolean, error: any }}
 */
export function useConflictReassignments() {
  return useFetch(fetchConflictReassignments, "conflict-reassignments");
}

/**
 * Fetch evidence items that were submitted after a decision was recorded.
 *
 * @returns {{ data: any, loading: boolean, error: any }}
 */
export function usePostDecisionEvidence() {
  return useFetch(fetchPostDecisionEvidence, "post-decision-evidence");
}

/**
 * Fetch appeals that lack an independent reviewer review.
 *
 * @returns {{ data: any, loading: boolean, error: any }}
 */
export function useAppealsWithoutIndependentReview() {
  return useFetch(
    fetchAppealsWithoutIndependentReview,
    "appeals-without-independent-review"
  );
}
