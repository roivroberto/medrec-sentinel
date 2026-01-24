# %% [markdown]
# MedGemma Challenge - Kaggle Submission Notebook
#
# This is a plain .py notebook scaffold ("# %%" cells) that can be:
# - uploaded directly to Kaggle (Kaggle supports script notebooks), or
# - converted locally: jupyter nbconvert --to notebook --execute notebooks/kaggle_submission.py
#
# Goals:
# - Run the baseline eval (no model weights required)
# - Optionally run the MedGemma eval if deps + weights are available

# %%
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def is_kaggle() -> bool:
    return bool(
        os.environ.get("KAGGLE_URL_BASE")
        or os.environ.get("KAGGLE_KERNEL_RUN_TYPE")
        or Path("/kaggle").exists()
    )


def find_repo_root() -> Path:
    env = os.environ.get("MEDREC_SENTINEL_ROOT")
    if env:
        return Path(env).resolve()

    here = Path(".").resolve()
    if (here / "medrec_sentinel").exists():
        return here

    kaggle_input = Path("/kaggle/input")
    if kaggle_input.exists():
        for p in kaggle_input.iterdir():
            if p.is_dir() and (p / "medrec_sentinel").exists():
                return p.resolve()

    raise RuntimeError(
        "Could not locate repo root. Set MEDREC_SENTINEL_ROOT to your repo folder "
        "(e.g. /kaggle/input/<dataset> or /kaggle/working/<repo>)."
    )


ROOT = find_repo_root()
DATA = ROOT / "data" / "synth" / "cases.jsonl"

# For Kaggle, always run code from /kaggle/working (writable).
RUN_CWD = Path("/kaggle/working") if is_kaggle() else ROOT
RUN_CWD.mkdir(parents=True, exist_ok=True)

# Make repo importable even when running from /kaggle/working.
ENV = os.environ.copy()
ENV["PYTHONPATH"] = str(ROOT) + os.pathsep + ENV.get("PYTHONPATH", "")
sys.path.insert(0, str(ROOT))


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=str(RUN_CWD), env=ENV)


print("repo_root:", ROOT)
print("data_path:", DATA)
print("run_cwd:", RUN_CWD)

# %% [markdown]
# 1) Install deps
#
# Kaggle images typically come with torch preinstalled (including CUDA on GPU runtimes).
# This project avoids force-installing torch by default.
#
# If you get import errors, uncomment the install cell.

# %%
# run([sys.executable, "-m", "pip", "install", "-q", "-r", str(ROOT / "requirements.txt")])
#
# # Optional GPU-only deps (bitsandbytes). Only enable if you know you need it.
# # run([sys.executable, "-m", "pip", "install", "-q", "-r", str(ROOT / "requirements-gpu.txt")])

# %% [markdown]
# 2) Baseline eval (no model required)

# %%
if not DATA.exists():
    raise FileNotFoundError(
        f"Missing {DATA}.\n\n"
        "In Kaggle: attach this repo as a Dataset (mounted under /kaggle/input/<dataset>), "
        "or set MEDREC_SENTINEL_ROOT to that dataset path."
    )

run(
    [
        sys.executable,
        "-m",
        "medrec_sentinel.eval.run_eval",
        "--data",
        str(DATA),
        "--mode",
        "baseline",
    ]
)

# %% [markdown]
# 3) Optional: MedGemma eval
#
# Requirements:
# - Kaggle Secret: HUGGINGFACE_TOKEN (or HF_TOKEN) with access to google/medgemma-4b-it
# - Sufficient RAM/VRAM for model loading (GPU runtime recommended)
#
# If you cannot access HF from Kaggle, an alternative is to upload the weights as a Kaggle Dataset and
# point transformers to that local folder.

# %%
maybe_token = os.environ.get("HUGGINGFACE_TOKEN") or os.environ.get("HF_TOKEN")
if not maybe_token:
    print("Skipping medgemma eval: HUGGINGFACE_TOKEN/HF_TOKEN not set.")
else:
    # Optional: pre-download weights into models/ (helps avoid repeated downloads)
    # run(
    #     [
    #         sys.executable,
    #         str(ROOT / "scripts" / "download_model.py"),
    #         "--model-id",
    #         "google/medgemma-4b-it",
    #     ]
    # )

    try:
        run(
            [
                sys.executable,
                "-m",
                "medrec_sentinel.eval.run_eval",
                "--data",
                str(DATA),
                "--mode",
                "medgemma",
            ]
        )
    except Exception as e:
        print("medgemma eval failed (continuing):", type(e).__name__, e)
