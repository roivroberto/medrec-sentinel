# MedRec Sentinel (MedGemma Impact Challenge)

Audit-first medication reconciliation for discharge workflows.

This project targets the **Agentic Workflow Prize**: MedGemma is used as a callable
extraction tool inside a larger workflow that validates outputs, runs deterministic
safety checks, and produces a pharmacist-facing draft note with verification questions.

Safety notes:
- Do not use with real PHI.
- Outputs are drafts for clinician review (not medical advice).

## Start Here (Judges)

- Narrative + architecture: `docs/writeup_3pager.md`
- Demo walkthrough script (<= 3 min): `docs/demo_script.md`
- Kaggle Writeup draft (template headings): `docs/kaggle_writeup.md`

## Quickstart (Baseline, No Model Required)

```bash
python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
pip install -r requirements-dev.txt

pytest -q

python3 -m medrec_sentinel.eval.run_eval --data data/synth/cases.jsonl --mode baseline

python3 demo/gradio_app.py
```

## Baseline Eval (No Model Required)

```bash
python3 -m medrec_sentinel.eval.run_eval --data data/synth/cases.jsonl --mode baseline
```

## Demo (Gradio)

```bash
python3 demo/gradio_app.py
```

## Optional: MedGemma Mode

MedGemma weights on Hugging Face are typically gated. If you have access:

1) Accept the model terms on Hugging Face
2) Create an access token
3) Export it as an env var (local shell or Kaggle Secret):

```bash
export HUGGINGFACE_TOKEN=hf_your_token_here
```

Then download weights into `models/`:

```bash
python3 scripts/download_model.py

# or override the repo id
python3 scripts/download_model.py --model-id google/medgemma-4b-it
```

Kaggle: set `HUGGINGFACE_TOKEN` as a Kaggle Secret, then run `notebooks/kaggle_submission.py`.

## Kaggle Notes

- `/kaggle/input` is read-only. Write outputs and model downloads under `/kaggle/working`.
- `scripts/download_model.py` defaults to `/kaggle/working/models` when it detects Kaggle.
- `notebooks/kaggle_submission.py` will auto-detect the repo under `/kaggle/input/<dataset>`.
  - If auto-detect fails, set `MEDREC_SENTINEL_ROOT=/kaggle/input/<dataset>`.

## Kaggle Submission

For a concise, step-by-step checklist (video link + Kaggle Writeup + repo link), see:
- `docs/kaggle_submission.md`
