# MedRec Sentinel (MedGemma Impact Challenge)

## 1. Problem and user

Medication reconciliation (med rec) at discharge is a frequent source of preventable harm. Discharge notes are messy, medication lists are incomplete, and high-risk combinations (e.g., anticoagulant + NSAID) can be missed under time pressure.

**Target user:** inpatient pharmacist (or clinician doing discharge med review).

**Goal:** turn free-text discharge content into a structured, auditable med rec review note that highlights high-risk issues and prompts verification.

## 2. Solution overview

MedRec Sentinel is a hybrid system:

- **Baseline extractor (fully reproducible):** deterministic heuristics extract meds from common discharge note patterns.
- **MedGemma extractor (optional upgrade):** uses Google Health AI Developer Foundations (HAI-DEF) model MedGemma to convert messy discharge text into strict JSON (medications, allergies, optional eGFR). This requires gated weights.
- **Deterministic risk engine:** applies a small curated medication safety knowledge base (auditable rules + citations) to generate risk flags.
- **Human-centered output:** produces a pharmacist-facing draft note with risks, verification questions, citations, and a clear disclaimer.

### Baseline vs MedGemma (what's reproducible)

- **baseline mode (default):** no model download required; runs anywhere.
- **medgemma mode (optional):** requires model weights; improves extraction robustness on real-world note variability.

Why this matters for judges: baseline demonstrates end-to-end feasibility and auditability; MedGemma is an incremental upgrade, not a dependency.

### Workflow (happy path)

1) Paste discharge note
2) Extract meds/allergies/eGFR (baseline regex or MedGemma)
3) Run deterministic checks (DDI, duplication, renal risk, allergy conflicts)
4) Present:
   - extracted meds table
   - risk flags + citations
   - draft pharmacist note for signoff

## 3. System design

**Core modules**

- `medrec_sentinel/extract/baseline.py`: deterministic baseline extractor
- `medrec_sentinel/llm/medgemma.py`: safe generation wrapper (JSON-only)
- `medrec_sentinel/extract/meds.py`: extraction prompt + robust JSON parsing
- `medrec_sentinel/rules/knowledge_base.py`: curated rules + citations
- `medrec_sentinel/rules/engine.py`: deterministic matching
- `medrec_sentinel/report/note.py`: draft pharmacist note template
- `medrec_sentinel/pipeline/run_case.py`: orchestrator

**Why this is human-centered**

- The model is not asked to "decide" a clinical action.
- Risk checks are deterministic and cite sources.
- Output is designed for review, not autonomous execution.

## 4. Data and evaluation

### Dataset

We ship a small, de-identified synthetic dataset:

- `data/synth/cases.jsonl`
- Includes labeled scenarios:
  - penicillin allergy + amoxicillin
  - ACE inhibitor duplication (lisinopril + benazepril)
  - metformin with low eGFR
  - warfarin + NSAID

### Metrics

We evaluate two core steps:

1) **Medication extraction micro-F1** vs `gold_med_names`
2) **Risk flag micro-PRF** vs `gold_flag_types`

Run:

```bash
python3 -m medrec_sentinel.eval.run_eval --data data/synth/cases.jsonl --mode baseline
```

Optional (if MedGemma deps + weights are available):

```bash
python3 -m medrec_sentinel.eval.run_eval --data data/synth/cases.jsonl --mode medgemma
```

## 5. Results (synthetic dataset)

Reproduce:

```bash
python3 -m medrec_sentinel.eval.run_eval --data data/synth/cases.jsonl --mode baseline
python3 -m medrec_sentinel.eval.run_eval --data data/synth/cases.jsonl --mode medgemma
```

Baseline results on `data/synth/cases.jsonl`:

| Mode | Success rate | Med extraction micro-F1 | Risk flags micro-Precision | Risk flags micro-Recall | Risk flags micro-F1 | Notes |
|------|--------------|--------------------------|----------------------------|--------------------------|---------------------|-------|
| baseline | 100% | 0.5857 | 0.5714 | 1.0000 | 0.7273 | fully reproducible |
| medgemma | - | - | - | - | - | requires gated weights |

## 6. Example (1 case, end-to-end)

Input (synthetic):

```text
Discharge meds: warfarin 5 mg daily, ibuprofen 400 mg prn.
Allergies: NKDA
```

Output (baseline or MedGemma extraction + deterministic rules):

- Extracted meds: `warfarin`, `ibuprofen`
- Flags:
  - `bleed_risk` (high): "Warfarin plus NSAID increases bleeding risk (platelet inhibition/GI injury) even if INR unchanged."
  - Citation example: "Warfarin (FDA label): concomitant NSAIDs may increase risk of bleeding."

Draft pharmacist note excerpt:

```text
Identified risks
1. [HIGH] bleed_risk: Warfarin plus NSAID increases bleeding risk (platelet inhibition/GI injury) even if INR unchanged.
   Citations: Warfarin (FDA label): concomitant NSAIDs may increase risk of bleeding.

Suggested verification questions
- Can you verify or clarify for 'bleed_risk': Warfarin plus NSAID increases bleeding risk (platelet inhibition/GI injury) even if INR unchanged?

Disclaimer
This note is not medical advice. It is generated for clinical decision support and must be reviewed...
```

## 7. Safety and limitations

**Safety posture**

- "Not medical advice" disclaimer in every note.
- Deterministic rules with citations (auditable).
- Extraction prompt instructs the model to treat the note as untrusted data and ignore embedded instructions.

**Known limitations**

- Synthetic evaluation is a starting point; real-world deployment would require local validation on institutional data and clinical governance.
- Rule coverage is intentionally small; expanding requires careful curation to avoid false positives.
- Brand names / abbreviations are not fully covered (deterministic synonym map is a future extension).

## 8. Deployment feasibility

- Runs locally (privacy-first) with baseline mode.
- MedGemma mode supports local GPU inference when weights are available.
- Integrates naturally as a side-panel in a discharge workflow: clinician remains in control.
