import { useState, useEffect } from "react";
import { fetchSubmissions } from "../api/submissions";

/**
 * Hook for fetching a paginated, filtered list of submissions.
 *
 * @param {object} filters - Filter params (e.g. { flagged: true })
 * @param {number} page - Current page number
 * @param {number} pageSize - Number of items per page
 * @returns {{ data: any, loading: boolean, error: any }}
 */
export function useSubmissions(filters = {}, page = 1, pageSize = 20) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // JSON.stringify filters to avoid infinite re-renders when a new object
  // reference is passed on every render with the same logical value.
  const filtersKey = JSON.stringify(filters);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchSubmissions({ ...filters, page, page_size: pageSize })
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtersKey, page, pageSize]);

  return { data, loading, error };
}
