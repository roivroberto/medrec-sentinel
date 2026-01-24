from __future__ import annotations


def test_demo_run_returns_agent_trace_text() -> None:
    from demo.gradio_app import run_case_for_demo

    meds_rows, flags_rows, note, trace = run_case_for_demo(
        discharge_note="Discharge meds: warfarin, ibuprofen.",
        allergies_text="",
        egfr=None,
        mode="baseline",
        override_extracted=False,
    )

    assert isinstance(meds_rows, list)
    assert isinstance(flags_rows, list)
    assert isinstance(note, str)
    assert isinstance(trace, str)
    assert "extract_baseline" in trace
    assert "total" in trace
