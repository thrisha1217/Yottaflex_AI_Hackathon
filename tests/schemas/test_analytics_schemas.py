"""Verification that analytics schemas serialise correctly.

Validates: Requirements 19.1–19.5
"""

from backend.schemas.analytics import (
    AssessmentCaseCount,
    CasesOverTimeOut,
    MonthlyCaseCount,
    OutcomesByProgramOut,
    ProgramOutcomes,
    ScoreBucket,
    SimilarityDistributionOut,
    SummaryOut,
    TopAssessmentsOut,
)


# ---------------------------------------------------------------------------
# Nested data items
# ---------------------------------------------------------------------------


def test_monthly_case_count():
    item = MonthlyCaseCount(month="2026-01", count=24)
    assert item.month == "2026-01"
    assert item.count == 24


def test_monthly_case_count_field_set():
    assert set(MonthlyCaseCount.model_fields.keys()) == {"month", "count"}


def test_program_outcomes():
    item = ProgramOutcomes(
        program="Computer Science",
        NO_VIOLATION=40,
        VIOLATION=10,
        INCONCLUSIVE=5,
    )
    assert item.program == "Computer Science"
    assert item.NO_VIOLATION == 40
    assert item.VIOLATION == 10
    assert item.INCONCLUSIVE == 5


def test_program_outcomes_field_set():
    assert set(ProgramOutcomes.model_fields.keys()) == {
        "program",
        "NO_VIOLATION",
        "VIOLATION",
        "INCONCLUSIVE",
    }


def test_assessment_case_count():
    item = AssessmentCaseCount(
        assessment_id="ASM-001", title="Research Essay", case_count=22
    )
    assert item.assessment_id == "ASM-001"
    assert item.title == "Research Essay"
    assert item.case_count == 22


def test_assessment_case_count_field_set():
    assert set(AssessmentCaseCount.model_fields.keys()) == {
        "assessment_id",
        "title",
        "case_count",
    }


def test_score_bucket():
    item = ScoreBucket(bucket="0-10", count=1850)
    assert item.bucket == "0-10"
    assert item.count == 1850


def test_score_bucket_field_set():
    assert set(ScoreBucket.model_fields.keys()) == {"bucket", "count"}


# ---------------------------------------------------------------------------
# SummaryOut (19.1)
# ---------------------------------------------------------------------------


def test_summary_out_construction():
    summary = SummaryOut(
        total_submissions=10000,
        flagged_submissions=1000,
        total_cases=300,
        total_decisions=300,
        total_appeals=90,
    )
    assert summary.total_submissions == 10000
    assert summary.flagged_submissions == 1000
    assert summary.total_cases == 300
    assert summary.total_decisions == 300
    assert summary.total_appeals == 90


def test_summary_out_field_set():
    assert set(SummaryOut.model_fields.keys()) == {
        "total_submissions",
        "flagged_submissions",
        "total_cases",
        "total_decisions",
        "total_appeals",
    }


def test_summary_out_has_from_attributes():
    assert SummaryOut.model_config.get("from_attributes") is True


# ---------------------------------------------------------------------------
# CasesOverTimeOut (19.2)
# ---------------------------------------------------------------------------


def test_cases_over_time_out():
    out = CasesOverTimeOut(
        data=[
            MonthlyCaseCount(month="2026-01", count=24),
            MonthlyCaseCount(month="2026-02", count=18),
        ]
    )
    assert len(out.data) == 2
    assert out.data[0].month == "2026-01"
    assert out.data[1].count == 18


def test_cases_over_time_out_empty():
    out = CasesOverTimeOut(data=[])
    assert out.data == []


def test_cases_over_time_out_field_set():
    assert set(CasesOverTimeOut.model_fields.keys()) == {"data"}


# ---------------------------------------------------------------------------
# OutcomesByProgramOut (19.3)
# ---------------------------------------------------------------------------


def test_outcomes_by_program_out():
    out = OutcomesByProgramOut(
        data=[
            ProgramOutcomes(
                program="Computer Science",
                NO_VIOLATION=40,
                VIOLATION=10,
                INCONCLUSIVE=5,
            )
        ]
    )
    assert len(out.data) == 1
    assert out.data[0].program == "Computer Science"
    assert out.data[0].VIOLATION == 10


def test_outcomes_by_program_out_field_set():
    assert set(OutcomesByProgramOut.model_fields.keys()) == {"data"}


# ---------------------------------------------------------------------------
# TopAssessmentsOut (19.4)
# ---------------------------------------------------------------------------


def test_top_assessments_out():
    out = TopAssessmentsOut(
        data=[
            AssessmentCaseCount(
                assessment_id="ASM-001", title="Research Essay", case_count=22
            ),
            AssessmentCaseCount(
                assessment_id="ASM-005", title="Final Exam", case_count=15
            ),
        ]
    )
    assert len(out.data) == 2
    assert out.data[0].assessment_id == "ASM-001"
    assert out.data[1].case_count == 15


def test_top_assessments_out_field_set():
    assert set(TopAssessmentsOut.model_fields.keys()) == {"data"}


# ---------------------------------------------------------------------------
# SimilarityDistributionOut (19.5)
# ---------------------------------------------------------------------------


def test_similarity_distribution_out():
    out = SimilarityDistributionOut(
        data=[
            ScoreBucket(bucket="0-10", count=1850),
            ScoreBucket(bucket="91-100", count=12),
        ]
    )
    assert len(out.data) == 2
    assert out.data[0].bucket == "0-10"
    assert out.data[1].count == 12


def test_similarity_distribution_out_field_set():
    assert set(SimilarityDistributionOut.model_fields.keys()) == {"data"}
