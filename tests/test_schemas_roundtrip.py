from __future__ import annotations


def test_case_input_json_roundtrip() -> None:
    from medrec_sentinel.schemas import CaseInput

    case = CaseInput(
        case_id="case-001",
        discharge_note="58M with HTN. Start lisinopril 10 mg PO daily. Hold if SBP < 100.",
        known_allergies=["penicillin"],
        egfr_ml_min_1_73m2=72.5,
    )

    payload = case.model_dump_json()
    parsed = CaseInput.model_validate_json(payload)

    assert parsed.model_dump() == case.model_dump()


def test_pipeline_output_json_dump_has_required_keys() -> None:
    from medrec_sentinel.schemas import (
        EvidenceSpan,
        Medication,
        PipelineOutput,
        RiskFlag,
    )

    out = PipelineOutput(
        case_id="case-001",
        extracted_medications=[
            Medication(
                name="lisinopril",
                dose="10 mg",
                route="PO",
                frequency="daily",
                prn=False,
                start="2026-01-01",
            )
        ],
        extracted_allergies=["penicillin"],
        risk_flags=[
            RiskFlag(
                flag_type="hypotension",
                severity="medium",
                summary="Lisinopril may worsen low blood pressure.",
                evidence_spans=[
                    EvidenceSpan(start=0, end=43, text="Start lisinopril 10 mg PO daily")
                ],
                citations=["note"],
            )
        ],
        pharmacist_note="Consider holding lisinopril if SBP < 100.",
        model_metadata={"model": "stub"},
    )

    required_keys = {
        "case_id",
        "extracted_medications",
        "extracted_allergies",
        "risk_flags",
        "pharmacist_note",
        "model_metadata",
    }

    assert required_keys.issubset(out.model_dump().keys())
