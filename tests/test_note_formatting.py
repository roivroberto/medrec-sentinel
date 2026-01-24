from medrec_sentinel.report.note import build_pharmacist_note
from medrec_sentinel.schemas import EvidenceSpan, RiskFlag


def test_note_collapses_whitespace_and_filters_empty_citations() -> None:
    flag = RiskFlag(
        flag_type="drug\ninteraction",
        severity="high\npriority",
        summary="Avoid   combo\nof X and\tY.",
        evidence_spans=[
            EvidenceSpan(start=0, end=10, text="Line 1\nLine 2"),
        ],
        citations=["", "  ", "Example\n guideline"],
    )

    note = build_pharmacist_note([flag])

    assert "[HIGH PRIORITY] drug interaction: Avoid combo of X and Y." in note
    assert "- Line 1 Line 2" in note
    assert "Citations: Example guideline" in note


def test_note_dedupes_verification_questions() -> None:
    flags = [
        RiskFlag(
            flag_type="test-flag",
            severity="high",
            summary="Example summary",
            citations=[],
        ),
        RiskFlag(
            flag_type="test-flag",
            severity="high",
            summary="Example summary",
            citations=[],
        ),
    ]

    note = build_pharmacist_note(flags)

    question = "- Can you verify or clarify for 'test-flag': Example summary?"
    assert note.count(question) == 1


def test_note_verification_questions_none_identified_when_no_flags() -> None:
    note = build_pharmacist_note([])

    assert "Suggested verification questions\n- None identified.\n" in note
