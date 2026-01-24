"""Gradio demo app.

This module is intentionally lightweight at import time:
- It does not import gradio unless the demo is executed.
- It does not load any models at import time.
"""

from __future__ import annotations

import sys
import traceback
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from medrec_sentinel.schemas import CaseInput


def _parse_allergies(allergies_text: str) -> list[str]:
    parts = [p.strip() for p in allergies_text.replace("\n", ",").split(",")]
    return [p for p in parts if p]


def _build_case_input(
    *,
    discharge_note: str,
    allergies_text: str,
    egfr: float | None,
    mode: str,
    override_extracted: bool,
) -> CaseInput:
    from medrec_sentinel.schemas import CaseInput

    if mode not in {"baseline", "medgemma"}:
        raise ValueError(f"Unknown mode: {mode}")

    base: dict[str, object] = {
        "case_id": str(uuid.uuid4()),
        "discharge_note": discharge_note,
    }

    allergies_text = allergies_text.strip()

    if mode == "medgemma":
        # If override_extracted is on, always set fields (even empty/None) so
        # run_case() sees them in model_fields_set and they win precedence.
        if override_extracted:
            base["known_allergies"] = (
                _parse_allergies(allergies_text) if allergies_text else []
            )
            base["egfr_ml_min_1_73m2"] = float(egfr) if egfr is not None else None
        else:
            # When blank, omit keys so they don't override extracted values.
            if allergies_text:
                base["known_allergies"] = _parse_allergies(allergies_text)
            if egfr is not None:
                base["egfr_ml_min_1_73m2"] = float(egfr)
    else:
        # Baseline mode doesn't extract allergies/eGFR.
        base["known_allergies"] = _parse_allergies(allergies_text) if allergies_text else []
        base["egfr_ml_min_1_73m2"] = float(egfr) if egfr is not None else None

    return CaseInput.model_validate(base)


def _humanize(text: str) -> str:
    """Convert snake_case to Title Case."""
    if not text:
        return ""
    # Special acronym handling could go here
    return text.replace("_", " ").title()


def _format_trace(trace: object, model_metadata: dict[str, object] | None = None) -> str:
    if not isinstance(trace, list):
        return "<div class='trace-empty'>No execution trace available.</div>"

    # Build Header (System Metadata)
    header_html = ""
    if model_metadata:
        items = []
        for k in ("mode", "model_id", "device_map", "max_new_tokens"):
             v = model_metadata.get(k)
             if isinstance(v, str) and v:
                 label = _humanize(k)
                 items.append(f"<div class='meta-item'><span class='meta-key'>{label}</span><span class='meta-val'>{v}</span></div>")
        
        if items:
            header_html = f"""
            <div class="trace-header">
                <div class="trace-title">SYSTEM KERNEL METADATA</div>
                <div class="meta-grid">{''.join(items)}</div>
            </div>
            """

    # Build Timeline
    rows = []
    total_ms = 0
    
    # Calculate total time first for relative bars (optional, but good for visualization)
    # For now, we'll just list them cleanly.
    
    for i, entry in enumerate(trace):
        if not isinstance(entry, dict):
            continue
        step = entry.get("step")
        ms = entry.get("ms")
        
        if not isinstance(step, str) or not step:
            continue
            
        step_display = _humanize(step)
        
        ms_display = "----"
        if isinstance(ms, int):
            ms_display = f"{ms}ms"
            total_ms += ms
            
        # Determine status color/icon based on step name or just generic success
        status_class = "status-ok"
        
        row_html = f"""
        <div class="trace-row">
            <div class="trace-status {status_class}"></div>
            <div class="trace-content">
                <div class="trace-step">{step_display}</div>
            </div>
            <div class="trace-time">{ms_display}</div>
        </div>
        """
        rows.append(row_html)

    if not rows:
        return header_html + "<div class='trace-empty'>Trace list empty.</div>"

    footer_html = f"""
    <div class="trace-footer">
        <span class="total-label">Total Execution Time</span>
        <span class="total-time">{total_ms}ms</span>
    </div>
    """

    return f"""
    <div class="trace-container">
        {header_html}
        <div class="trace-body">
            {''.join(rows)}
        </div>
        {footer_html}
    </div>
    """


def run_case_for_demo(
    *,
    discharge_note: str,
    allergies_text: str,
    egfr: float | None,
    mode: str,
    override_extracted: bool,
) -> tuple[list[list[str]], list[list[str]], str, str]:
    from medrec_sentinel.pipeline.run_case import run_case
    from medrec_sentinel.report.note import build_pharmacist_note_text

    case = _build_case_input(
        discharge_note=discharge_note,
        allergies_text=allergies_text,
        egfr=egfr,
        mode=mode,
        override_extracted=override_extracted,
    )
    out = run_case(case, mode=mode)

    meds_rows: list[list[str]] = [
        [
            m.name,
            m.dose or "",
            m.route or "",
            m.frequency or "",
            str(bool(m.prn)),
            m.start or "",
            m.stop or "",
        ]
        for m in out.extracted_medications
    ]

    flags_rows: list[list[str]] = [
        [
            f.severity.upper(),
            _humanize(f.flag_type),
            f.summary,
            "; ".join(f.citations),
        ]
        for f in out.risk_flags
    ]

    trace_text = ""
    trace = out.model_metadata.get("trace")
    # Pass metadata for header generation
    trace_text = _format_trace(trace, out.model_metadata)
    
    trace_text = _format_trace(trace, out.model_metadata)
    
    # Generate plain text note
    note_text = build_pharmacist_note_text(out.risk_flags)
    
    return meds_rows, flags_rows, out.pharmacist_note, trace_text, note_text


def sign_note(note_html: str) -> str:
    """Simulate a digital signature on the HTML note."""
    if not note_html:
        return note_html
    
    # 1. Update Status
    note_html = note_html.replace("DRAFT - NOT FINAL", "FINAL REPORT")
    
    # 2. Add Signature
    note_html = note_html.replace(
        "__________________________________________", 
        "Victor"
    )
    
    # 3. Add Timestamp
    # We replace the placeholders.
    from datetime import datetime
    now = datetime.now()
    note_html = note_html.replace(
        "DATE: <span class=\"signoff-date\">____/____/________</span>",
        f"DATE: <span class=\"signoff-date\">{now.strftime('%Y-%m-%d')}</span>"
    )
    note_html = note_html.replace(
        "TIME: <span class=\"signoff-time\">____:____</span>",
        f"TIME: <span class=\"signoff-time\">{now.strftime('%H:%M')}</span>"
    )
    
    return note_html


def build_demo():
    """Return a gradio Blocks app.

    Kept as a function to avoid importing gradio during tests.
    """

    import gradio as gr
    from gradio.themes.utils import colors, sizes

    # -------------------------------------------------------------------------
    # Swiss Clinical Theme Definition (Native API)
    # -------------------------------------------------------------------------
    theme = gr.themes.Base(
        primary_hue=colors.neutral,
        neutral_hue=colors.neutral,
        font=[gr.themes.GoogleFont("Sora"), "sans-serif"],
        font_mono=[gr.themes.GoogleFont("JetBrains Mono"), "monospace"],
        radius_size=sizes.radius_none,
    ).set(
        # Body & General Config
        body_background_fill="#ffffff",
        body_text_color="#000000",
        body_text_size="15px",
        
        # Block / Panel Styles
        block_background_fill="#ffffff",
        block_border_width="2px",
        block_border_color="#000000",
        block_label_background_fill="#ffffff",
        block_label_text_color="#000000",
        block_label_text_weight="800", # Bold labels
        block_title_text_color="#000000",
        block_title_text_weight="800",
        
        # Input Fields
        input_background_fill="#000000",
        input_border_color="#000000",
        input_border_width="2px",
        input_radius="0px",
        input_padding="16px",
        input_text_weight="500",
        input_placeholder_color="#ffffff",
        
        # Buttons
        button_primary_background_fill="#000000",
        button_primary_background_fill_hover="#0044cc", # Clinical Blue on Hover
        button_primary_text_color="#ffffff",
        button_primary_border_color="#000000",
        button_transition="all 0.1s ease",
        
        # Tables (Dataframes)
        table_border_color="#000000",
        table_text_color="#000000",
        
        # Layout
        section_header_text_size="1.1rem", # Standardized header size
        section_header_text_weight="800",
        block_label_text_size="1.1rem", # Consistency with headers
    )

    # -------------------------------------------------------------------------
    # Supplemental CSS (Things specifically not covered by Theme API)
    # -------------------------------------------------------------------------
    # - Grid background for headers
    # - Specific table header typography that Theme API handles loosely
    # - Removing border radii deeper in the stack
    SUPPLEMENTAL_CSS = """
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;800&family=Oxygen:wght@300;400;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    /* Layout Details */
    .bg-grid {
        background-image: 
            linear-gradient(#eee 1px, transparent 1px),
            linear-gradient(90deg, #eee 1px, transparent 1px);
        background-size: 20px 20px;
    }
    
    /* Title Area Visibility Fix */
    .title-container {
        background: #ffffff;
        border: 4px solid #000000;
        padding: 20px;
        position: relative;
        z-index: 10;
    }

    /* Force Title Text Dark */
    .title-container h1 {
        color: #000000 !important;
    }
    
    /* Force Uppercase & Styling on all labels/headers */
    span.label-wrap, label span, .gradio-accordion-label, th {
        text-transform: uppercase !important;
        font-family: 'Sora', sans-serif !important;
        letter-spacing: 0.05em !important;
    }
    
    .gr-dataframe thead th {
        background: #000000 !important;
        color: #ffffff !important;
        padding: 12px !important;
    }
    
    /* Input Visibility Helpers - INVERTED */
    textarea, input, .gr-input, .gr-box {
        background-color: #000000 !important;
        color: #ffffff !important;
        border: 2px solid #000000 !important;
    }
    
    ::placeholder {
        opacity: 1 !important;
        color: #ffffff !important; 
        font-weight: 500;
    }
    
    /* Utility Badges */
    .badge-alert {
        display: inline-block;
        background: #ff3b30;
        color: white;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        font-weight: 700;
        padding: 4px 8px;
        text-transform: uppercase;
        border: 2px solid #000;
        margin-right: 5px;
    }
    
    /* Pagination Improvements */
    .paginate {
        display: flex !important;
        justify-content: center !important;
        gap: 10px !important;
        margin-top: 15px !important;
        align-items: center !important;
    }
    
    .paginate button {
        background: #ffffff !important;
        color: #000000 !important;
        border: 2px solid #000000 !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 800 !important;
        font-size: 1rem !important;
        padding: 4px 12px !important;
        border-radius: 0px !important;
        box-shadow: 2px 2px 0px #000000 !important;
        transition: all 0.1s ease !important;
        margin: 0 !important;
    }
    
    .paginate button:hover {
        background: #000000 !important;
        color: #ffffff !important;
    }
    
    .paginate button.selected {
        background: #000000 !important;
        color: #ffffff !important;
        transform: translate(2px, 2px);
        box-shadow: none !important;
    }
    
    /* Fix Arrow Visibility - Gradio often uses SVG icons */
    .paginate svg {
        fill: currentColor !important;
        width: 16px !important;
        height: 16px !important;
    }

    /* -------------------------------------------------------------------------
       SYSTEM TRACE UI
       ------------------------------------------------------------------------- */
    .trace-container {
        font-family: 'JetBrains Mono', monospace;
        background: #000000;
        color: #ffffff;
        border: 2px solid #000000;
        padding: 0;
        height: 100%;
        display: flex;
        flex-direction: column;
    }

    .trace-header {
        background: #1a1a1a;
        padding: 12px;
        border-bottom: 1px solid #333;
    }

    .trace-title {
        color: #888;
        font-size: 0.75rem;
        font-weight: 700;
        margin-bottom: 8px;
        letter-spacing: 0.05em;
    }

    .meta-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 8px;
        font-size: 0.8rem;
    }

    .meta-item {
        display: flex;
        gap: 8px;
    }

    .meta-key {
        color: #666;
    }

    .meta-val {
        color: #00ccff; /* Cyan for data */
        font-weight: 600;
    }

    .trace-body {
        padding: 12px;
        flex-grow: 1;
        overflow-y: auto;
        min-height: 200px; /* Ensure visibility */
    }

    .trace-row {
        display: flex;
        align-items: center;
        padding: 8px 0;
        border-bottom: 1px solid #1a1a1a;
    }

    .trace-row:last-child {
        border-bottom: none;
    }

    .trace-status {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 12px;
        flex-shrink: 0;
    }

    .status-ok {
        background-color: #00ff41; /* CRT Green */
        box-shadow: 0 0 5px #00ff41;
    }

    .trace-content {
        flex-grow: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .trace-step {
        font-weight: 500;
        color: #ddd;
    }

    .trace-time {
        color: #ffcc00; /* Amber for timings */
        font-weight: 700;
        margin-left: 12px;
        min-width: 60px;
        text-align: right;
    }

    .trace-footer {
        background: #1a1a1a;
        padding: 10px 12px;
        border-top: 1px solid #333;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.85rem;
    }

    .total-label {
        color: #888;
        font-weight: 700;
    }

    .total-time {
        color: #00ff41;
        font-weight: 800;
        font-size: 1rem;
    }

    .trace-empty {
        padding: 20px;
        text-align: center;
        color: #555;
        font-style: italic;
    }

    /* -------------------------------------------------------------------------
       EHR NOTE UI (DARK THEME)
       ------------------------------------------------------------------------- */
    .ehr-container {
        color: #ddd;
        background: #000;
        padding: 20px;
        border: 2px solid #333;
        font-family: 'JetBrains Mono', monospace;
        line-height: 1.5;
        height: 100%;
        overflow-y: auto;
    }

    .ehr-header {
        border-bottom: 2px solid #333;
        padding-bottom: 15px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .ehr-title {
        font-family: 'Sora', sans-serif;
        font-size: 1.4rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #fff;
    }

    .ehr-status {
        color: #888;
        font-size: 0.8rem;
        border: 1px solid #555;
        padding: 4px 8px;
        background: #111;
    }

    .ehr-section {
        margin-bottom: 25px;
    }

    .ehr-section-title {
        font-family: 'Sora', sans-serif;
        font-size: 0.9rem;
        font-weight: 700;
        text-transform: uppercase;
        color: #888;
        border-bottom: 1px solid #333;
        margin-bottom: 12px;
        padding-bottom: 4px;
        letter-spacing: 0.05em;
    }

    .ehr-empty {
        font-style: italic;
        color: #666;
        font-size: 0.9rem;
    }

    /* Risk Items */
    .ehr-risk-item {
        background: #111;
        border-left: 4px solid #444;
        padding: 12px;
        margin-bottom: 12px;
    }

    .ehr-risk-header {
        display: flex;
        align-items: center;
        margin-bottom: 6px;
        gap: 10px;
    }

    .ehr-severity {
        font-family: 'JetBrains Mono', monospace;
        font-weight: 800;
        font-size: 0.7rem;
        padding: 2px 8px;
        color: #000;
        text-transform: uppercase;
    }

    .sev-high { background: #ff3b30; color: #fff; box-shadow: 0 0 5px #ff3b30; }
    .sev-mod { background: #ffcc00; color: #000; }
    .sev-default { background: #888; color: #000; }

    .ehr-risk-type {
        font-family: 'Sora', sans-serif;
        font-weight: 700;
        font-size: 1rem;
        color: #fff;
    }

    .ehr-risk-summary {
        font-size: 0.95rem;
        margin-bottom: 8px;
        color: #ccc;
    }

    .ehr-evidence-label {
        font-size: 0.8rem;
        font-weight: 700;
        color: #666;
        text-transform: uppercase;
        margin-top: 8px;
    }

    .ehr-evidence-list {
        margin: 0;
        padding-left: 20px;
        font-size: 0.9rem;
        color: #aaa;
    }

    .ehr-citations {
        margin-top: 10px;
        font-size: 0.8rem;
        color: #00ccff; /* Data Cyan */
    }

    /* Questions */
    .ehr-questions-list {
        padding-left: 20px;
        margin: 0;
        color: #ccc;
    }
    .ehr-questions-list li {
        margin-bottom: 6px;
    }
    .ehr-questions-list b {
        color: #fff;
    }

    /* Disclaimer & Signoff */
    .ehr-disclaimer {
        font-size: 0.75rem;
        color: #555;
        border-top: 1px solid #333;
        padding-top: 12px;
        margin-bottom: 25px;
    }

    .ehr-signoff {
        margin-top: 30px;
        background: #1a1a1a;
        padding: 20px;
        border: 1px dashed #444;
        display: flex;
        flex-direction: column;
        gap: 12px;
    }

    .signoff-line {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
    }

    .signoff-label {
        font-weight: 700;
        text-transform: uppercase;
        font-size: 0.8rem;
        color: #888;
    }

    .signoff-signature {
        color: #00ccff; /* Digital Blue/Cyan */
        font-family: 'Cursive', serif;
        font-size: 1.4rem;
        text-shadow: 0 0 2px #00ccff;
    }

    .signoff-meta {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        color: #666;
        text-align: right;
    }
    """

    EXAMPLE_WARFARIN_NSAID = """Discharge meds: warfarin 5 mg daily, ibuprofen 400 mg prn.

Allergies: NKDA
"""

    EXAMPLE_METFORMIN_EGFR = """Discharge meds: metformin 500 mg bid.

Labs: eGFR 25 mL/min/1.73m2
"""

    def _run(
        discharge_note: str,
        allergies_text: str,
        egfr: float | None,
        mode: str,
        override_extracted: bool,
    ):
        if not discharge_note.strip():
            return [], [], "Error: discharge note is required.", ""

        try:
            meds_rows, flags_rows, note_html, trace, note_text = run_case_for_demo(
                discharge_note=discharge_note,
                allergies_text=allergies_text,
                egfr=egfr,
                mode=mode,
                override_extracted=override_extracted,
            )
            return meds_rows, flags_rows, note_html, trace, note_text
        except Exception:
            error_id = str(uuid.uuid4())
            print(
                f"[gradio_demo_error:{error_id}]\n{traceback.format_exc()}",
                file=sys.stderr,
            )
            return [], [], f"Error running pipeline (error id: {error_id}).", "", ""

    with gr.Blocks(title="MEDREC // SENTINEL", theme=theme, css=SUPPLEMENTAL_CSS) as demo:
        
        # HEADER
        with gr.Row(elem_classes="bg-grid", variant="panel"):
            with gr.Column(scale=4):
                gr.HTML("""
                <div class="title-container">
                    <h1 style="font-size: 2.5rem; margin-bottom: 5px;">MEDREC <span style="color: #0044cc">//</span> SENTINEL</h1>
                    <div style="font-family: 'JetBrains Mono', monospace; color: #555; margin-bottom: 10px; font-weight: 600;">
                        AUTOMATED PHARMACIST INTELLIGENCE UNIT v1.0
                    </div>
                    <div>
                        <span class="badge-alert">CLINICAL DEMO SYSTEM</span>
                        <span class="badge-alert" style="background: #111;">NOT FOR PATIENT USE</span>
                    </div>
                </div>
                """)

        # MAIN CONTENT GRID
        with gr.Row():
            
            # LEFT PANEL: DATA INPUT
            with gr.Column(scale=1, variant="default"):
                gr.Markdown("### // INPUT DATASTREAM")
                
                discharge_in = gr.Textbox(
                    label="DISCHARGE SUMMARY SOURCE",
                    lines=15,
                    placeholder="PASTE CLINICAL TEXT SEQUENCE...",
                    show_label=True,
                )
                
                with gr.Row():
                    allergies_in = gr.Textbox(
                        label="HISTORICAL ALLERGIES",
                        placeholder="COMMA-SEPARATED",
                        lines=1,
                    )
                    egfr_in = gr.Number(
                        label="eGFR [mL/min]",
                        precision=1,
                    )
                
                with gr.Accordion("// SYSTEM CONFIGURATION", open=False):
                    mode_in = gr.Radio(
                        choices=["baseline", "medgemma"],
                        value="baseline",
                        label="INFERENCE ENGINE",
                        info="BASELINE: REGEX HEURISTICS | MEDGEMMA: LLM 4B-INT4",
                    )
                    override_in = gr.Checkbox(
                        label="FORCE CONTEXT OVERRIDE",
                        value=False,
                    )

                run_btn = gr.Button("INITIALIZE ANALYSIS SEQUENCE", variant="primary")

                gr.Examples(
                    examples=[
                        [EXAMPLE_WARFARIN_NSAID, "", None, "baseline", False],
                        [EXAMPLE_WARFARIN_NSAID, "", None, "medgemma", False],
                        [EXAMPLE_METFORMIN_EGFR, "", None, "baseline", False],
                        [EXAMPLE_METFORMIN_EGFR, "", None, "medgemma", False],
                    ],
                    inputs=[discharge_in, allergies_in, egfr_in, mode_in, override_in],
                    label="TEST VECTORS",
                    examples_per_page=2,
                )

            # RIGHT PANEL: ANALYSIS OUTPUT
            with gr.Column(scale=1, variant="default"):
                with gr.Tabs():
                    with gr.TabItem("NOTE GENERATION", id=0):
                        note_out = gr.HTML(
                            label="PHARMACIST RECONCILIATION NOTE",
                        )
                        with gr.Row():
                            sign_btn = gr.Button("SIGN & FINALIZE", variant="primary")
                    
                    with gr.TabItem("RAW TEXT", id=4):
                        note_text_out = gr.Textbox(
                            label="PLAIN TEXT EXPORT",
                            show_copy_button=True,
                            interactive=False,
                            lines=20,
                        )
                    
                    with gr.TabItem("RISK MATRIX", id=1):
                        flags_out = gr.Dataframe(
                            label="DETECTED SAFETY SIGNALS",
                            headers=["SEVERITY", "TYPE", "SUMMARY", "EVIDENCE"],
                            wrap=True,
                            interactive=False,
                        )
                    
                    with gr.TabItem("EXTRACTION LOG", id=2):
                        meds_out = gr.Dataframe(
                            label="IDENTIFIED PHARMACEUTICALS",
                            headers=["NAME", "DOSE", "ROUTE", "FREQ", "PRN", "START", "STOP"],
                            interactive=False,
                        )
                    
                    with gr.TabItem("SYSTEM TRACE", id=3):
                        trace_out = gr.HTML(
                            label="KERNEL EXECUTION TRACE",
                        )

        run_btn.click(
            fn=_run,
            inputs=[discharge_in, allergies_in, egfr_in, mode_in, override_in],
            outputs=[meds_out, flags_out, note_out, trace_out, note_text_out],
        )

        sign_btn.click(
            fn=sign_note,
            inputs=[note_out],
            outputs=[note_out],
        )
        
        # Reset just re-runs extraction? Or we specifically need to store state.
        # For simplicity, let's just make it clear running again resets it.
        # Actually, let's wire it to undo the changes if possible, but regex undo is hard.
        # Better: Run button resets it automatically. The reset button here strictly for the note 
        # would require state management. Let's just rely on re-run.
        # UPDATE: User asked for interaction. Let's make "Reset" just be a clear or something?
        # No, let's remove the Reset button logic if it's too complex without state.
        # But wait, I added the button in the UI above. Let's just make it do nothing or re-set to Input?
        # Actually, simpler: The Run button already generates a fresh unsigned note.
        # So "Reset Signature" could theoretically just be hidden or output a "Draft" string if we had it.
        # Since we don't store the "Original" note in a State variable, we can't truly "Reset" without re-running.
        # I will remove the Reset button from logic if I can't back it up, OR I will update the logic to use State.
        # Let's keep it simple: Only SIGN button for now, I will remove Reset button in the UI tweak if needed,
        # or just not wire it and let it be a placeholder? No, that's bad.
        # I'll rely on the user re-running the case to reset.
        # Re-reading my plan: "Add a standard gr.Button("RESET SIGNATURE") (optional)".
        # I'll leave it unwired for a second and then realize I should probably remove it or Wire it to something.
        # Actually, I'll remove it from the UI definition in the previous chunk if I can... 
        # Too late, I'm issuing one tool call. I will just NOT wire it, and maybe user won't notice, 
        # OR I can wire it to a dummy function that says "Re-run analysis to reset".
        # Better: I will wire it to `lambda: None` with a js alert? No.
        # I will just remove it from the UI in the replacement above. 
        # Wait, I can't edit the previous chunk in thought.
        # I will change the UI chunk above to NOT include the reset button.

    return demo


def main() -> None:
    try:
        demo = build_demo()
    except ModuleNotFoundError as exc:
        missing = getattr(exc, "name", None) or str(exc)
        raise SystemExit(
            "Missing optional dependency for demo: "
            f"{missing}. Install gradio to run this app."
        ) from exc

    demo.launch()


if __name__ == "__main__":
    main()
