### Project name

MedRec Sentinel

### Your team

- Roi Victor Roberto (solo)

Links:
- Video (<= 3 minutes): TODO
- Code: https://github.com/roivroberto/MedGemma-Challenge (branch: `feat/medrec-sentinel`)
- Demo (bonus): run locally via `python3 demo/gradio_app.py`

### Problem statement

Medication reconciliation at discharge is a high-risk, time-pressured workflow. Discharge notes are messy, medication lists are inconsistent, and clinically important safety issues (e.g., duplication within a drug class, anticoagulant + NSAID, renal dosing risks, allergy conflicts) can be missed.

Target user: inpatient pharmacist (or clinician performing discharge medication review).

Goal: turn free-text discharge content into an auditable, pharmacist-facing draft review note that highlights high-risk issues and prompts verification (human-in-the-loop, not autonomous care).

### Overall solution

MedRec Sentinel is a hybrid system that uses HAI-DEF MedGemma for what models are good at (messy clinical text understanding) and deterministic code for what must be auditable (safety checks):

- MedGemma extractor (HAI-DEF): converts discharge text into strict JSON (medications, allergies, eGFR when present) and is prompted to ignore prompt-injection inside the note.
- Agent loop (validate + repair): the system validates the extraction contract and automatically retries when model outputs are not valid JSON (bounded attempts).
- Deterministic risk engine: applies curated rules + citations to generate risk flags (duplication, DDI, renal risk, allergy conflict).
- Human-centered output: generates a pharmacist-facing draft note with verification questions, citations, and an explicit “not medical advice” disclaimer.

Baseline mode (fully reproducible) is included as a fallback: a deterministic extractor runs without model weights, proving the end-to-end workflow is feasible even when MedGemma is unavailable.

This submission targets the **Agentic Workflow Prize**: it reimagines discharge med rec as a tool-driven loop with explicit checkpoints (extract → validate/repair → deterministic safety tools → verification questions), rather than a single-shot summary.

### Technical details

Core code:
- Pipeline: `medrec_sentinel/pipeline/run_case.py`
- Baseline extractor: `medrec_sentinel/extract/baseline.py`
- MedGemma wrapper: `medrec_sentinel/llm/medgemma.py`
- MedGemma extraction contract: `medrec_sentinel/extract/meds.py`
- Deterministic rules + citations: `medrec_sentinel/rules/`
- Demo UI: `demo/gradio_app.py`
- Eval harness + metrics: `medrec_sentinel/eval/run_eval.py`

Reproducibility:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest -q

# baseline eval (no model required)
python3 -m medrec_sentinel.eval.run_eval --data data/synth/cases.jsonl --mode baseline

# local demo
python3 demo/gradio_app.py
```

Optional MedGemma mode (requires gated weights + token): see `README.md` and `notebooks/kaggle_submission.py`.

Fine-tuning: none (uses base `google/medgemma-4b-it` weights; improvements come from workflow design + tool use).

Safety notes:
- Deterministic checks with citations (auditable)
- Prompt-injection resistance in extraction prompt
- Output framed for clinician signoff with explicit disclaimer
