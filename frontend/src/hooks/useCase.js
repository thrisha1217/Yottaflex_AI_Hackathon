import { useState, useEffect } from "react";
import { fetchCase } from "../api/cases";
import { fetchEvidence } from "../api/evidence";
import { fetchDecisions } from "../api/decisions";
import { fetchAppeals } from "../api/appeals";

/**
 * Hook for fetching full case detail data including evidence, decisions, and appeals.
 *
 * Fetches all four resources in parallel via Promise.all when caseId is truthy.
 *
 * @param {string} caseId - The ID of the integrity case to load
 * @returns {{ caseData: any, evidence: any, decisions: any, appeals: any, loading: boolean, error: any }}
 */
export function useCase(caseId) {
  const [caseData, setCaseData] = useState(null);
  const [evidence, setEvidence] = useState(null);
  const [decisions, setDecisions] = useState(null);
  const [appeals, setAppeals] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!caseId) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    Promise.all([
      fetchCase(caseId),
      fetchEvidence(caseId),
      fetchDecisions(caseId),
      fetchAppeals(caseId),
    ])
      .then(([caseResult, evidenceResult, decisionsResult, appealsResult]) => {
        setCaseData(caseResult);
        setEvidence(evidenceResult);
        setDecisions(decisionsResult);
        setAppeals(appealsResult);
      })
      .catch(setError)
      .finally(() => setLoading(false));
  }, [caseId]);

  return { caseData, evidence, decisions, appeals, loading, error };
}
