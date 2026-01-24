from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

DEFAULT_MODEL_ID = "google/medgemma-4b-it"


def _safe_dirname(model_id: str) -> str:
    return (
        (model_id or "model")
        .strip()
        .replace("/", "__")
        .replace(":", "__")
        .replace(" ", "_")
    )


def _is_kaggle() -> bool:
    return bool(
        os.environ.get("KAGGLE_URL_BASE")
        or os.environ.get("KAGGLE_KERNEL_RUN_TYPE")
        or Path("/kaggle").exists()
    )


def _lazy_snapshot_download():
    try:
        from huggingface_hub import snapshot_download  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "huggingface_hub is required for model downloads. "
            "Install it with: pip install huggingface_hub\n\n"
            "Tip: transformers typically depends on huggingface_hub, so installing "
            "requirements.txt may already provide it."
        ) from e
    return snapshot_download


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="download-model",
        description=(
            "Download MedGemma weights via Hugging Face into a local models/ directory.\n\n"
            "Local strategy:\n"
            "- Set HUGGINGFACE_TOKEN (or HF_TOKEN) with an access token that can read the gated repo\n"
            "- Run this script once to populate a project-local HF cache + a copy under models/\n\n"
            "Kaggle strategy:\n"
            "- Add HUGGINGFACE_TOKEN as a Kaggle Secret (Environment variable)\n"
            "- Run this script in a notebook cell before running medgemma eval\n"
            "- If HF access is not possible, attach weights as a Kaggle Dataset and use a local path"
        ),
    )
    parser.add_argument(
        "--model-id",
        type=str,
        default=DEFAULT_MODEL_ID,
        help=f"Hugging Face model repo id (default: {DEFAULT_MODEL_ID})",
    )
    parser.add_argument(
        "--revision",
        type=str,
        default=None,
        help="Optional HF revision (branch/tag/commit)",
    )
    parser.add_argument(
        "--out-root",
        type=str,
        default=None,
        help=(
            "Root directory to write model artifacts. "
            "Defaults to /kaggle/working/models on Kaggle and ./models elsewhere."
        ),
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default=None,
        help="Optional HF cache dir (default: <out-root>/hf_cache)",
    )
    args = parser.parse_args(argv)

    is_kaggle = _is_kaggle()

    token = os.environ.get("HUGGINGFACE_TOKEN") or os.environ.get("HF_TOKEN")
    if not token:
        print(
            "warning: HUGGINGFACE_TOKEN (or HF_TOKEN) is not set. "
            "If the repo is gated, download will fail.",
            file=sys.stderr,
        )

    default_out_root = Path("/kaggle/working/models") if is_kaggle else Path("models")
    out_root = Path(args.out_root).expanduser().resolve() if args.out_root else default_out_root
    if is_kaggle and out_root.is_relative_to(Path("/kaggle/input")):
        raise SystemExit(
            "error: --out-root points to /kaggle/input (read-only). "
            "Use /kaggle/working/models."
        )
    out_root.mkdir(parents=True, exist_ok=True)

    cache_dir = (
        Path(args.cache_dir).expanduser().resolve()
        if args.cache_dir
        else (out_root / "hf_cache")
    )
    cache_dir.mkdir(parents=True, exist_ok=True)

    local_dir = out_root / _safe_dirname(args.model_id)
    local_dir.mkdir(parents=True, exist_ok=True)

    if is_kaggle:
        print("Kaggle detected: writing under /kaggle/working is recommended.")

    print(f"model_id:   {args.model_id}")
    print(f"cache_dir:  {cache_dir}")
    print(f"local_dir:  {local_dir}")

    snapshot_download = _lazy_snapshot_download()
    local_dir_use_symlinks = True if is_kaggle else False

    try:
        snapshot_download(
            repo_id=args.model_id,
            revision=args.revision,
            token=token,
            cache_dir=str(cache_dir),
            local_dir=str(local_dir),
            local_dir_use_symlinks=local_dir_use_symlinks,
        )
    except Exception as e:
        print("\nDownload failed.", file=sys.stderr)
        if not token:
            print(
                "This model likely requires authentication. Set HUGGINGFACE_TOKEN to a Hugging Face access token "
                "that can read the repository (gated models require accepting terms).",
                file=sys.stderr,
            )
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    print("\nDownload complete.")
    print(f"Model files available at: {local_dir}")
    print("\nTip: to keep all HF downloads inside the repo, set:")
    print(f"  export HF_HOME={cache_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
