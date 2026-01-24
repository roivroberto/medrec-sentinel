from __future__ import annotations

from typing import Any

import medrec_sentinel.eval.run_eval as run_eval
from medrec_sentinel.schemas import CaseInput, Medication, PipelineOutput, RiskFlag


def test_evaluate_mode_counts_failures_as_fn(monkeypatch) -> None:
    rows: list[dict[str, Any]] = [
        {
            "case_id": "case-1",
            "discharge_note": "Discharge meds: warfarin, ibuprofen.",
            "known_allergies": [],
            "egfr_ml_min_1_73m2": None,
            "gold_med_names": ["warfarin", "ibuprofen"],
            "gold_flag_types": ["bleed_risk"],
        },
        {
            "case_id": "case-2",
            "discharge_note": "Discharge meds: metformin 500 mg bid.",
            "known_allergies": [],
            "egfr_ml_min_1_73m2": 25.0,
            "gold_med_names": ["metformin"],
            "gold_flag_types": ["renal_risk"],
        },
    ]

    def fake_run_case(case: CaseInput, mode: str = "baseline"):
        if case.case_id == "case-2":
            raise RuntimeError("boom")

        assert mode == "baseline"
        return PipelineOutput(
            case_id=case.case_id,
            extracted_medications=[
                Medication(name="warfarin"),
                Medication(name="ibuprofen"),
            ],
            extracted_allergies=[],
            risk_flags=[
                RiskFlag(
                    type="bleed_risk",
                    severity="high",
                    summary="stub",
                    citations=[],
                )
            ],
            pharmacist_note="",
            model_metadata={"mode": "baseline"},
        )

    monkeypatch.setattr(run_eval, "run_case", fake_run_case)

    results = run_eval._evaluate_mode("baseline", rows)
    assert results["n_cases"] == 2
    assert results["n_ok"] == 1
    assert results["n_failed"] == 1
    assert results["first_error"]
    assert round(results["success_rate"], 2) == 0.50

    meds_f1 = results["medication_extraction"]["f1"]
    flags_f1 = results["risk_flags"]["f1"]
    assert round(meds_f1, 2) == 0.80
    assert round(flags_f1, 2) == 0.67
