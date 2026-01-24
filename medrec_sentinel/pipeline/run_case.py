"""Pipeline entrypoint.

Precedence rules (medgemma mode): values extracted from the note are used by
default, but user-provided inputs win when they were explicitly provided. We use
Pydantic's `model_fields_set` to distinguish an omitted field from a field that
was intentionally set to an empty list / None.

- Allergies: if `known_allergies` is explicitly provided, it overrides extracted.
- eGFR: if `egfr_ml_min_1_73m2` is explicitly provided (even as None), it
  overrides extracted.
"""

from __future__ import annotations

from medrec_sentinel.extract.baseline import extract_medications_baseline
from medrec_sentinel.extract.meds import extract_with_medgemma
from medrec_sentinel.llm.medgemma import default_model_id
from medrec_sentinel.report.note import build_pharmacist_note
from medrec_sentinel.rules.engine import run_risk_checks
from medrec_sentinel.schemas import CaseInput, PipelineOutput


def run_case(case: CaseInput, mode: str = "baseline") -> PipelineOutput:
    if mode not in {"baseline", "medgemma"}:
        raise ValueError("mode must be one of: baseline, medgemma")

    if mode == "baseline":
        meds = extract_medications_baseline(case.discharge_note)
        allergies = list(case.known_allergies)
        egfr = case.egfr_ml_min_1_73m2
        model_metadata: dict[str, object] = {"mode": "baseline"}
    else:
        extracted = extract_with_medgemma(case.discharge_note)
        meds = extracted.medications

        allergies = extracted.allergies
        if "known_allergies" in case.model_fields_set:
            allergies = list(case.known_allergies)

        egfr = extracted.egfr_ml_min_1_73m2
        if "egfr_ml_min_1_73m2" in case.model_fields_set:
            egfr = case.egfr_ml_min_1_73m2

        model_metadata = {"mode": "medgemma", "model_id": default_model_id()}

    flags = run_risk_checks(meds, allergies, egfr)
    note = build_pharmacist_note(flags)

    return PipelineOutput(
        case_id=case.case_id,
        extracted_medications=meds,
        extracted_allergies=allergies,
        risk_flags=flags,
        pharmacist_note=note,
        model_metadata=model_metadata,
    )
