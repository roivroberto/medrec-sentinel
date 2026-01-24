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


def build_demo():
    """Return a gradio Blocks app.

    Kept as a function to avoid importing gradio during tests.
    """

    import gradio as gr

    def _run(
        discharge_note: str,
        allergies_text: str,
        egfr: float | None,
        mode: str,
        override_extracted: bool,
    ):
        if not discharge_note.strip():
            return [], [], "Error: discharge note is required."

        try:
            from medrec_sentinel.pipeline.run_case import run_case

            case = _build_case_input(
                discharge_note=discharge_note,
                allergies_text=allergies_text,
                egfr=egfr,
                mode=mode,
                override_extracted=override_extracted,
            )
            out = run_case(case, mode=mode)

            meds_rows = [
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

            flags_rows = [
                [
                    f.severity,
                    f.flag_type,
                    f.summary,
                    "; ".join(f.citations),
                ]
                for f in out.risk_flags
            ]

            return meds_rows, flags_rows, out.pharmacist_note
        except Exception:
            error_id = str(uuid.uuid4())
            print(
                f"[gradio_demo_error:{error_id}]\n{traceback.format_exc()}",
                file=sys.stderr,
            )
            return [], [], f"Error running pipeline (error id: {error_id})."

    with gr.Blocks(title="MedRec Sentinel Demo") as demo:
        gr.Markdown(
            "# MedRec Sentinel\n\n"
            "Paste a discharge note, optionally provide allergies/eGFR, and run "
            "either the baseline extractor or MedGemma.\n\n"
            "MedGemma precedence: leave allergies/eGFR blank to use extracted values; "
            "enable override to force your inputs (including empty/None)."
        )

        with gr.Row():
            mode_in = gr.Radio(
                choices=["baseline", "medgemma"],
                value="baseline",
                label="Mode",
            )

        discharge_in = gr.Textbox(
            label="Discharge note",
            lines=16,
            placeholder="Paste discharge note text here...",
        )

        with gr.Row():
            allergies_in = gr.Textbox(
                label="Allergies (optional, comma-separated)",
                placeholder="e.g. penicillin, sulfa",
            )
            egfr_in = gr.Number(
                label="eGFR (optional)",
                precision=2,
            )

        override_in = gr.Checkbox(
            label="Override extracted allergies/eGFR (MedGemma only)",
            value=False,
        )

        run_btn = gr.Button("Run", variant="primary")

        meds_out = gr.Dataframe(
            label="Extracted meds",
            headers=["name", "dose", "route", "frequency", "prn", "start", "stop"],
            datatype=["str", "str", "str", "str", "str", "str", "str"],
            row_count=(0, "dynamic"),
            col_count=(7, "fixed"),
        )
        flags_out = gr.Dataframe(
            label="Risk flags",
            headers=["severity", "type", "summary", "citations"],
            datatype=["str", "str", "str", "str"],
            row_count=(0, "dynamic"),
            col_count=(4, "fixed"),
        )
        note_out = gr.Textbox(label="Pharmacist note", lines=10)

        run_btn.click(
            fn=_run,
            inputs=[discharge_in, allergies_in, egfr_in, mode_in, override_in],
            outputs=[meds_out, flags_out, note_out],
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
