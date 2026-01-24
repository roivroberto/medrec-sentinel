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

import os
import time

from medrec_sentinel.extract.baseline import extract_medications_baseline
from medrec_sentinel.extract.meds import extract_with_medgemma
from medrec_sentinel.llm.medgemma import default_model_id
from medrec_sentinel.report.note import build_pharmacist_note
from medrec_sentinel.rules.engine import run_risk_checks
from medrec_sentinel.schemas import CaseInput, PipelineOutput


def _append_trace(
    trace: list[dict[str, object]],
    *,
    step: str,
    start_s: float,
    end_s: float,
    **extra: object,
) -> None:
    entry: dict[str, object] = {
        "step": step,
        "ms": int((end_s - start_s) * 1000.0),
    }
    entry.update(extra)
    trace.append(entry)


def run_case(case: CaseInput, mode: str = "baseline") -> PipelineOutput:
    if mode not in {"baseline", "medgemma"}:
        raise ValueError("mode must be one of: baseline, medgemma")

    trace: list[dict[str, object]] = []
    t_total_start = time.perf_counter()

    if mode == "baseline":
        t0 = time.perf_counter()
        meds = extract_medications_baseline(case.discharge_note)
        _append_trace(trace, step="extract_baseline", start_s=t0, end_s=time.perf_counter())
        allergies = list(case.known_allergies)
        egfr = case.egfr_ml_min_1_73m2
        model_metadata: dict[str, object] = {"mode": "baseline", "trace": trace}
    else:
        t0 = time.perf_counter()
        extracted = extract_with_medgemma(case.discharge_note)
        _append_trace(trace, step="extract_medgemma", start_s=t0, end_s=time.perf_counter())
        meds = extracted.medications

        allergies = extracted.allergies
        if "known_allergies" in case.model_fields_set:
            allergies = list(case.known_allergies)

        egfr = extracted.egfr_ml_min_1_73m2
        if "egfr_ml_min_1_73m2" in case.model_fields_set:
            egfr = case.egfr_ml_min_1_73m2

        model_metadata = {
            "mode": "medgemma",
            "model_id": default_model_id(),
            "device_map": os.environ.get("MEDGEMMA_DEVICE_MAP", "auto"),
            "max_new_tokens": os.environ.get("MEDGEMMA_MAX_NEW_TOKENS", "256"),
            "trace": trace,
        }

    t0 = time.perf_counter()
    flags = run_risk_checks(meds, allergies, egfr)
    _append_trace(trace, step="risk_checks", start_s=t0, end_s=time.perf_counter())

    t0 = time.perf_counter()
    note = build_pharmacist_note(flags)
    _append_trace(trace, step="build_note", start_s=t0, end_s=time.perf_counter())

    _append_trace(trace, step="total", start_s=t_total_start, end_s=time.perf_counter())

    return PipelineOutput(
        case_id=case.case_id,
        extracted_medications=meds,
        extracted_allergies=allergies,
        risk_flags=flags,
        pharmacist_note=note,
        model_metadata=model_metadata,
    )
