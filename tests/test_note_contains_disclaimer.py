from medrec_sentinel.report.note import build_pharmacist_note
from medrec_sentinel.schemas import RiskFlag


def test_note_contains_disclaimer_and_citations() -> None:
    flag = RiskFlag(
        flag_type="test-flag",
        severity="high",
        summary="Example summary",
        citations=["Example guideline"],
    )

    note = build_pharmacist_note([flag])

    assert "not medical advice" in note.lower()
    assert "Example guideline" in note
    assert note.endswith("\n")
