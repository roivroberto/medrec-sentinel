from __future__ import annotations


def test_run_case_baseline_smoke_flags_warfarin_nsaid() -> None:
    from medrec_sentinel.pipeline.run_case import run_case
    from medrec_sentinel.schemas import CaseInput

    case = CaseInput(
        case_id="case_001",
        discharge_note="Discharge meds: warfarin, ibuprofen.",
        known_allergies=[],
        egfr_ml_min_1_73m2=None,
    )
    out = run_case(case, mode="baseline")

    assert out.case_id == "case_001"
    assert len(out.risk_flags) >= 1

    med_names = {m.name for m in out.extracted_medications}
    assert {"warfarin", "ibuprofen"}.issubset(med_names)
