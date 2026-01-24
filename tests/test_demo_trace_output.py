from __future__ import annotations


def test_demo_run_returns_agent_trace_text() -> None:
    from demo.gradio_app import run_case_for_demo

    meds_rows, flags_rows, note_html, trace, note_text = run_case_for_demo(
        discharge_note="Discharge meds: warfarin, ibuprofen.",
        allergies_text="",
        egfr=None,
        mode="baseline",
        override_extracted=False,
    )

    assert isinstance(meds_rows, list)
    assert isinstance(flags_rows, list)
    assert isinstance(note_html, str)
    assert isinstance(trace, str)
    
    # Verify HTML structure
    assert "class=\"trace-container\"" in trace
    assert "class=\"trace-row\"" in trace
    # Should now be humanized
    assert "Extract Baseline" in trace  
    assert "Total Execution Time" in trace
