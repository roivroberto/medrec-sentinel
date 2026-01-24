# MedRec Sentinel Demo Script (<= 3 minutes)

## Audience

Judges (Google Research / DeepMind / Google Health AI). Assume they care about impact, feasibility, safety, and clarity.

## Setup (before recording)

- Have the Gradio app ready: `python3 demo/gradio_app.py`
- Prepare 2 example discharge notes:
  - One that triggers warfarin + NSAID
  - One that triggers metformin + low eGFR
- Have a terminal tab ready to run baseline eval: `python3 -m medrec_sentinel.eval.run_eval --data data/synth/cases.jsonl --mode baseline`

## Timeline

### 0:00 - 0:15 Problem

- "Medication reconciliation at discharge is a high-risk, time-pressured workflow. Missed interactions and duplications can cause harm."
- "We built MedRec Sentinel: a pharmacist-in-the-loop tool that turns messy discharge text into an auditable safety review note."

### 0:15 - 0:30 Who it is for

- "Target user: inpatient pharmacist reviewing discharge meds."
- "The tool does not prescribe. It flags risks and generates a structured draft note for signoff."

### 0:30 - 1:50 Live demo (baseline mode first)

1) Paste the example discharge note.
2) Select `baseline`.
3) Click Run.
4) Narrate outputs:
   - extracted medication table
   - risk flags (severity + type + summary + citations)
   - pharmacist note with verification questions and disclaimer

### 1:50 - 2:20 What MedGemma adds

- Switch to `medgemma` mode.
- Explain:
  - "MedGemma converts messy text into strict JSON (meds, allergies, eGFR when present)."
  - "Deterministic rule engine does the safety checks; citations are auditable."

- Call out one concrete before/after (example):
  - "On a messy note with comma lists, section headers, or free-text allergies, baseline extraction can miss entities; MedGemma is more robust because it is trained for medical text understanding."

If model weights aren't available on your recording machine, narrate this step with a screenshot and say baseline mode remains fully reproducible.

### 2:20 - 2:45 Evaluation + reproducibility

- Run the eval command and show the printed table.
- "We report medication extraction micro-F1 and risk flag PRF on a labeled dataset."
- "Errors are counted (failed cases become false negatives), keeping metrics honest."

### 2:45 - 3:00 Safety + close

- "Safety: prompt injection resistance in extraction prompt, deterministic rules with citations, explicit disclaimer and signoff."
- "This is designed to plug into discharge med rec as decision support, not autonomous care."
