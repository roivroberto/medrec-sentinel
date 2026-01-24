from __future__ import annotations


def test_run_case_includes_agent_trace_in_metadata() -> None:
    from medrec_sentinel.pipeline.run_case import run_case
    from medrec_sentinel.schemas import CaseInput

    case = CaseInput(
        case_id="case-1",
        discharge_note="Discharge meds: warfarin, ibuprofen.",
        known_allergies=[],
        egfr_ml_min_1_73m2=None,
    )

    out = run_case(case, mode="baseline")
    trace = out.model_metadata.get("trace")

    assert isinstance(trace, list)
    assert trace

    steps = [e.get("step") for e in trace if isinstance(e, dict)]
    assert "extract_baseline" in steps
    assert "risk_checks" in steps
    assert "build_note" in steps

    # Basic sanity: each trace entry includes an integer ms duration.
    for e in trace:
        if not isinstance(e, dict):
            continue
        if "ms" in e:
            assert isinstance(e["ms"], int)
            assert e["ms"] >= 0
