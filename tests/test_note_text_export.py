from __future__ import annotations

from medrec_sentinel.report.note import build_pharmacist_note_text
from medrec_sentinel.schemas import RiskFlag


def test_note_text_export_format() -> None:
    flag = RiskFlag(
        flag_type="drug_interaction",
        severity="high_priority",
        summary="Avoid combo.",
        citations=["Guideline 1"]
    )
    
    text = build_pharmacist_note_text([flag])
    
    # Ensure NO HTML tags
    assert "<div>" not in text
    assert "<b>" not in text
    assert "class=" not in text
    
    # Ensure content is present and formatted
    assert "PHARMACIST NOTE (DRAFT)" in text
    assert "1. [HIGH PRIORITY] Drug Interaction: Avoid combo." in text
    assert "Citations: Guideline 1" in text
    assert "Clinician signoff" in text
