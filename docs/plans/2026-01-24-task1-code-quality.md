# Task 1 Code Quality Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make installs Kaggle-friendly and improve repo hygiene without changing runtime behavior.

**Architecture:** Keep default dependencies CPU-safe; isolate GPU-only extras into a separate requirements file. Ensure editable installs work via minimal setuptools package discovery.

**Tech Stack:** Python, setuptools (PEP 517/518), pytest.

---

### Task 1: Fix runtime requirements for Kaggle

**Files:**
- Modify: `requirements.txt`
- Create: `requirements-gpu.txt`

**Step 1: Remove torch and GPU-only deps from default requirements**

Edit `requirements.txt` so it does not include `torch` (or other GPU-only deps like `bitsandbytes`).

**Step 2: Add GPU extras file**

Create `requirements-gpu.txt` with at least:

```text
bitsandbytes
```

Optionally mention `torch` as a comment (do not force-install it by default).

### Task 2: Add dev tooling requirements

**Files:**
- Create: `requirements-dev.txt`

**Step 1: Add minimal dev tool deps**

Create `requirements-dev.txt` containing:

```text
pytest
ruff
black
```

### Task 3: Make editable installs work

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add minimal setuptools package discovery**

Add a `[tool.setuptools.packages.find]` section that includes `medrec_sentinel*`.

### Task 4: Add top-level .gitignore

**Files:**
- Create: `.gitignore`

**Step 1: Add common Python ignores**

Include common Python artifacts plus `.worktrees/` and `outputs/`.

### Task 5: Verify

**Step 1: Run tests**

Run:

```bash
~/.venvs/medrec-sentinel/bin/python -m pytest -q
```
