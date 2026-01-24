# MedGemma-Challenge

## Docs (start here if you're judging)

- `docs/writeup_3pager.md` (project narrative)
- `docs/demo_script.md` (<= 3 min walkthrough)
- `docs/clinical_rubric.md` (how we'd evaluate with clinicians)

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
pip install -r requirements-dev.txt

pytest -q

python3 -m medrec_sentinel.eval.run_eval --data data/synth/cases.jsonl --mode baseline

python3 demo/gradio_app.py
```

## Baseline eval (no model required)

```bash
python3 -m medrec_sentinel.eval.run_eval --data data/synth/cases.jsonl --mode baseline
```

## Demo (Gradio)

```bash
python3 demo/gradio_app.py
```

## Download MedGemma weights

MedGemma on Hugging Face is typically gated. You need to:

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

Kaggle tip: set `HUGGINGFACE_TOKEN` as a Kaggle Secret, then run `notebooks/kaggle_submission.py`.

## Kaggle notes

- `/kaggle/input` is read-only. Write outputs and model downloads under `/kaggle/working`.
- `scripts/download_model.py` defaults to `/kaggle/working/models` when it detects Kaggle.
- `notebooks/kaggle_submission.py` will auto-detect the repo under `/kaggle/input/<dataset>`.
  - If auto-detect fails, set `MEDREC_SENTINEL_ROOT=/kaggle/input/<dataset>`.
