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

    # Check for HTML structure
    assert "<div class=\"ehr-risk-item\">" in note
    
    # Check humanized and cleaned text
    # Severity is now UPPERCASE in the badge
    assert "HIGH PRIORITY" in note 
    assert "Drug Interaction" in note
    assert "Avoid combo of X and Y." in note
    
    # Check evidence listing
    assert "<li>Line 1 Line 2</li>" in note
    
    # Check citations
    assert "Refs: Example guideline" in note


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
    
    question_part = "Can you verify or clarify for <b>Test-Flag</b>: Example summary?"
    assert note.count(question_part) == 1


def test_note_verification_questions_none_identified_when_no_flags() -> None:
    note = build_pharmacist_note([])

    assert "<div class='ehr-empty'>None identified.</div>" in note
