# MedRec Sentinel - Clinician/Pharmacist Review Rubric

## Purpose

Collect structured feedback to support a realistic impact narrative. This is a research prototype; reviewers should assume outputs require clinician confirmation.

## Materials

- 5-10 de-identified or synthetic discharge notes
- For each note: the tool output (extracted meds, risk flags, pharmacist note)

## Scoring (1-5)

For each case, rate:

1) **Correctness**
   - 1: mostly incorrect / unsafe
   - 3: mixed; some useful elements
   - 5: correct and clinically usable with review

2) **Usefulness / actionability**
   - Does it surface the right risks and make review easier?

3) **Trustworthiness**
   - Does the output feel grounded (citations, clear uncertainty)?

4) **Time saved (proxy)**
   - 1: slows me down
   - 3: neutral
   - 5: meaningfully speeds up review

5) **Safety / risk management**
   - Does it avoid overconfident recommendations? Are failure modes obvious?

## Binary questions

- Would you use this in a real discharge med rec workflow (with clinician signoff)? (yes/no)
- If no, what is the main blocker? (pick one)
  - too many false positives
  - too many misses
  - unclear citations / rationale
  - workflow mismatch
  - liability / governance
  - performance/latency

## Free-text prompts

- What was the single most useful part of the output?
- What was the most concerning failure mode you observed?
- What one change would most improve adoption?

## Notes for reporting

- Report number of reviewers, their role (pharmacist/physician), and number of cases reviewed.
- Include representative quotes (anonymized).
- Include at least one failure case and what would mitigate it.
