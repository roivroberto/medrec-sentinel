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


def _format_trace(trace: object) -> str:
    if not isinstance(trace, list):
        return ""

    lines: list[str] = []
    for entry in trace:
        if not isinstance(entry, dict):
            continue
        step = entry.get("step")
        ms = entry.get("ms")
        if not isinstance(step, str) or not step:
            continue
        if isinstance(ms, int):
            lines.append(f"- {step}: {ms} ms")
        else:
            lines.append(f"- {step}")

    return "\n".join(lines)


def run_case_for_demo(
    *,
    discharge_note: str,
    allergies_text: str,
    egfr: float | None,
    mode: str,
    override_extracted: bool,
) -> tuple[list[list[str]], list[list[str]], str, str]:
    from medrec_sentinel.pipeline.run_case import run_case

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
            f.severity,
            f.flag_type,
            f.summary,
            "; ".join(f.citations),
        ]
        for f in out.risk_flags
    ]

    trace_text = ""
    trace = out.model_metadata.get("trace")
    trace_text = _format_trace(trace)
    if trace_text:
        meta_items: list[str] = []
        for k in ("mode", "model_id", "device_map", "max_new_tokens"):
            v = out.model_metadata.get(k)
            if isinstance(v, str) and v:
                meta_items.append(f"{k}={v}")
        if meta_items:
            trace_text = "meta: " + ", ".join(meta_items) + "\n" + trace_text

    return meds_rows, flags_rows, out.pharmacist_note, trace_text


def build_demo():
    """Return a gradio Blocks app.

    Kept as a function to avoid importing gradio during tests.
    """

    import gradio as gr
    from gradio.themes import Soft

    css = """
:root {
  --ms-brand: #0f766e;
  --ms-brand-2: #115e59;
  --ms-ink: #0b1320;
  --ms-muted: #4b5563;
  --ms-bg: #f7f6f3;
  --ms-card: #ffffff;
  --ms-border: rgba(15, 23, 42, 0.10);
}

.gradio-container {
  background:
    radial-gradient(900px 500px at 12% 8%, rgba(15, 118, 110, 0.10), transparent 60%),
    radial-gradient(900px 500px at 88% 12%, rgba(2, 132, 199, 0.10), transparent 55%),
    radial-gradient(700px 420px at 70% 92%, rgba(244, 63, 94, 0.06), transparent 60%),
    var(--ms-bg);
  color: var(--ms-ink);
  font-family: "Noto Sans", "DejaVu Sans", "Liberation Sans", sans-serif;
}

#ms-hero {
  background: linear-gradient(135deg, rgba(15, 118, 110, 0.12), rgba(2, 132, 199, 0.10));
  border: 1px solid var(--ms-border);
  border-radius: 16px;
  padding: 16px 18px;
  margin-bottom: 12px;
}

#ms-hero h1 {
  margin: 0;
  font-size: 22px;
  letter-spacing: -0.02em;
}

#ms-hero p {
  margin: 6px 0 0 0;
  color: var(--ms-muted);
  line-height: 1.35;
}

.ms-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.ms-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid var(--ms-border);
  background: rgba(255, 255, 255, 0.65);
  color: var(--ms-ink);
  font-size: 12px;
}

.ms-badge strong {
  color: var(--ms-brand-2);
}

.ms-panel {
  background: var(--ms-card);
  border: 1px solid var(--ms-border);
  border-radius: 16px;
  padding: 14px 14px;
}

.ms-panel h3 {
  margin: 0 0 8px 0;
  font-size: 14px;
  letter-spacing: -0.01em;
}

.ms-hint {
  color: var(--ms-muted);
  font-size: 12px;
  margin-top: 6px;
}

.ms-status {
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid var(--ms-border);
  background: rgba(15, 118, 110, 0.06);
}
"""

    theme = Soft(
        primary_hue="teal",
        secondary_hue="cyan",
        neutral_hue="slate",
    )

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
        preview_baseline: bool,
    ):
        if not discharge_note.strip():
            yield (
                "<div class='ms-status'><strong>Error:</strong> discharge note is required.</div>",
                [],
                [],
                "",
                "",
            )
            return

        def _format_status(text: str) -> str:
            return f"<div class='ms-status'>{text}</div>"

        try:
            if mode == "medgemma" and preview_baseline:
                meds_rows, flags_rows, note, trace = run_case_for_demo(
                    discharge_note=discharge_note,
                    allergies_text=allergies_text,
                    egfr=egfr,
                    mode="baseline",
                    override_extracted=override_extracted,
                )
                yield (
                    _format_status(
                        "<strong>Baseline preview</strong> (fast) while MedGemma runs..."
                    ),
                    meds_rows,
                    flags_rows,
                    note,
                    trace,
                )

            meds_rows, flags_rows, note, trace = run_case_for_demo(
                discharge_note=discharge_note,
                allergies_text=allergies_text,
                egfr=egfr,
                mode=mode,
                override_extracted=override_extracted,
            )
            yield (
                _format_status(
                    f"<strong>Done.</strong> Mode: <code>{mode}</code>"
                ),
                meds_rows,
                flags_rows,
                note,
                trace,
            )
        except Exception:
            error_id = str(uuid.uuid4())
            print(
                f"[gradio_demo_error:{error_id}]\n{traceback.format_exc()}",
                file=sys.stderr,
            )
            yield (
                _format_status(
                    f"<strong>Error:</strong> pipeline failed (error id: <code>{error_id}</code>)."
                ),
                [],
                [],
                "",
                "",
            )

    with gr.Blocks(title="MedRec Sentinel Demo", theme=theme, css=css) as demo:
        gr.HTML(
            """
            <div id="ms-hero">
              <h1>MedRec Sentinel</h1>
              <p>
                Audit-first discharge medication reconciliation: extraction tool + schema validation + repair loop + deterministic safety checks.
              </p>
              <div class="ms-badges">
                <span class="ms-badge"><strong>Baseline</strong> reproducible</span>
                <span class="ms-badge"><strong>MedGemma</strong> optional</span>
                <span class="ms-badge"><strong>Agent trace</strong> visible</span>
                <span class="ms-badge"><strong>No PHI</strong> in demo</span>
              </div>
            </div>
            """
        )

        with gr.Row(equal_height=True):
            with gr.Column(scale=5):
                with gr.Group(elem_classes=["ms-panel"]):
                    gr.Markdown("### Inputs")
                    mode_in = gr.Radio(
                        choices=["baseline", "medgemma"],
                        value="baseline",
                        label="Mode",
                    )

                    discharge_in = gr.Textbox(
                        label="Discharge note",
                        lines=14,
                        placeholder="Paste discharge note text here...",
                    )

                    with gr.Row():
                        allergies_in = gr.Textbox(
                            label="Allergies (optional)",
                            placeholder="e.g. penicillin, sulfa",
                        )
                        egfr_in = gr.Number(
                            label="eGFR (optional)",
                            precision=2,
                        )

                    with gr.Row():
                        override_in = gr.Checkbox(
                            label="Override extracted allergies/eGFR (MedGemma)",
                            value=False,
                        )
                        preview_in = gr.Checkbox(
                            label="Show baseline preview while MedGemma runs",
                            value=True,
                        )

                    gr.Examples(
                        examples=[
                            [EXAMPLE_WARFARIN_NSAID, "", None, "baseline", False, True],
                            [EXAMPLE_WARFARIN_NSAID, "", None, "medgemma", False, True],
                            [EXAMPLE_METFORMIN_EGFR, "", None, "baseline", False, True],
                            [EXAMPLE_METFORMIN_EGFR, "", None, "medgemma", False, True],
                        ],
                        inputs=[
                            discharge_in,
                            allergies_in,
                            egfr_in,
                            mode_in,
                            override_in,
                            preview_in,
                        ],
                        label="Examples (synthetic)",
                    )

                    run_btn = gr.Button("Run", variant="primary")
                    gr.Markdown(
                        "<div class='ms-hint'>Tip: the first MedGemma run warms the model; subsequent runs are faster.</div>"
                    )

            with gr.Column(scale=7):
                with gr.Group(elem_classes=["ms-panel"]):
                    gr.Markdown("### Outputs")
                    status_out = gr.HTML(
                        "<div class='ms-status'><strong>Ready.</strong> Choose an example or paste a note.</div>"
                    )

                    with gr.Tabs():
                        with gr.Tab("Extracted"):
                            meds_out = gr.Dataframe(
                                label="Extracted meds",
                                headers=[
                                    "name",
                                    "dose",
                                    "route",
                                    "frequency",
                                    "prn",
                                    "start",
                                    "stop",
                                ],
                                datatype=[
                                    "str",
                                    "str",
                                    "str",
                                    "str",
                                    "str",
                                    "str",
                                    "str",
                                ],
                                row_count=(0, "dynamic"),
                                col_count=(7, "fixed"),
                            )

                        with gr.Tab("Risks"):
                            flags_out = gr.Dataframe(
                                label="Risk flags",
                                headers=["severity", "type", "summary", "citations"],
                                datatype=["str", "str", "str", "str"],
                                row_count=(0, "dynamic"),
                                col_count=(4, "fixed"),
                            )

                        with gr.Tab("Draft note"):
                            note_out = gr.Textbox(label="Pharmacist note", lines=14)

                        with gr.Tab("Agent trace"):
                            trace_out = gr.Textbox(
                                label="Agent trace (timings)",
                                lines=10,
                                interactive=False,
                            )

        run_btn.click(
            fn=_run,
            inputs=[
                discharge_in,
                allergies_in,
                egfr_in,
                mode_in,
                override_in,
                preview_in,
            ],
            outputs=[status_out, meds_out, flags_out, note_out, trace_out],
        )

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
