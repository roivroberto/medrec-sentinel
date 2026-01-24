# MedRec Sentinel Kaggle Submission Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Finalize `MedRec Sentinel` for MedGemma Impact Challenge submission (public repo + Kaggle Writeup + <=3 min video).

**Architecture:** Keep code + demo reproducible (baseline path), with optional MedGemma path gated by weights/token. Provide a Kaggle Writeup-ready markdown draft that follows the required template and links to public repo + video.

**Tech Stack:** Python, Pydantic, HF Transformers, bitsandbytes (optional), Gradio, Pytest, Ruff.

---

### Task 1: Final Verification (Local)

**Files:**
- None

**Step 1: Run lint**

Run:
```bash
.venv/bin/ruff check .
```
Expected: `All checks passed!`

**Step 2: Run tests**

Run:
```bash
.venv/bin/python -m pytest -q
```
Expected: `0 failed`

**Step 3: Run baseline eval smoke**

Run:
```bash
.venv/bin/python -m medrec_sentinel.eval.run_eval --data data/synth/cases.jsonl --mode baseline --limit 10
```
Expected: `baseline 10/10 ok` and `wrote: outputs/metrics.json`

**Step 4 (optional): Run medgemma eval smoke**

Run:
```bash
export MEDGEMMA_MODEL_ID="$(pwd)/models/google__medgemma-4b-it"
export TRANSFORMERS_OFFLINE=1
export HF_HUB_OFFLINE=1
export MEDGEMMA_DEVICE_MAP=auto
export MEDGEMMA_MAX_NEW_TOKENS=192
.venv/bin/python -m medrec_sentinel.eval.run_eval --data data/synth/cases.jsonl --mode medgemma --limit 3
```
Expected: `medgemma 3/3 ok`.

---

### Task 2: Create Kaggle Writeup Markdown (Template-Compliant)

**Files:**
- Create: `docs/kaggle_writeup.md`

**Step 1: Draft template-compliant writeup**

Create `docs/kaggle_writeup.md` with EXACT headings:

```markdown
### Project name

### Your team

### Problem statement

### Overall solution

### Technical details
```

Keep it <= 3 pages worth of content (short, link-heavy).

**Step 2: Add links placeholders**

Include placeholders the human will fill in:
- `Video:` <link>
- `Code:` https://github.com/roivroberto/MedGemma-Challenge (and/or PR link)
- `Demo (bonus):` <optional>

---

### Task 3: Publish Code Without Touching `main`

**Files:**
- None

**Step 1: Push feature branch**

Run:
```bash
git push -u origin feat/medrec-sentinel
```

**Step 2: Create PR (do not merge yet)**

Run:
```bash
gh pr create \
  --base main \
  --head feat/medrec-sentinel \
  --title "MedRec Sentinel: MedGemma + deterministic med safety" \
  --body "$(cat <<'EOF'
## Summary
- Add MedRec Sentinel pipeline (baseline + optional MedGemma extractor) with deterministic risk rules and Gradio demo.
- Add eval harness + synthetic labeled dataset + Kaggle submission notebook scaffold.
- Stabilize MedGemma inference on low-VRAM GPUs (4-bit NF4) and add robust JSON parsing/retry.

## Test Plan
- [x] .venv/bin/ruff check .
- [x] .venv/bin/python -m pytest -q
- [x] .venv/bin/python -m medrec_sentinel.eval.run_eval --data data/synth/cases.jsonl --mode baseline --limit 10
EOF
)"
```

---

### Task 4: Produce the <=3 Minute Video (Human)

**Files:**
- Use: `docs/demo_script.md`

**Step 1: Record screen capture**

Show:
- Gradio demo in baseline mode
- Briefly switch to medgemma mode (or explain + show screenshot if weights unavailable)
- Terminal run of baseline eval

**Step 2: Upload video and get share link**

Use an unlisted YouTube link or equivalent.

---

### Task 5: Create and Submit Kaggle Writeup (Human)

**Files:**
- Paste: `docs/kaggle_writeup.md` into Kaggle Writeup editor

**Step 1: Join hackathon**

On Kaggle competition page: click `Join Hackathon`.

**Step 2: Create writeup**

Go to `Writeups` tab -> `New Writeup`.

**Step 3: Fill required links**

Add:
- Video link (<=3 minutes)
- Public repo link (and optionally PR link)

**Step 4: Submit**

Click `Submit` in the top right.
