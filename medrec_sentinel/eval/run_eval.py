from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from medrec_sentinel.eval.metrics import micro_prf
from medrec_sentinel.pipeline.run_case import run_case
from medrec_sentinel.schemas import CaseInput

_PUNCT_RE = re.compile(r"[^a-z0-9\s]+")


def _normalize_med_name(text: str) -> str:
    low = (text or "").lower()
    low = _PUNCT_RE.sub(" ", low)
    low = re.sub(r"\s+", " ", low).strip()
    return low


def _normalize_flag_type(text: str) -> str:
    return (text or "").strip().lower()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _evaluate_mode(mode: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    med_pairs: list[tuple[set[str], set[str]]] = []
    flag_pairs: list[tuple[set[str], set[str]]] = []

    ok = 0
    failed = 0
    first_error: str | None = None
    error_print_limit = 3
    for i, row in enumerate(rows):
        gold_meds = {
            _normalize_med_name(m) for m in (row.get("gold_med_names") or []) if m
        }
        gold_meds.discard("")

        gold_flags = {
            _normalize_flag_type(f)
            for f in (row.get("gold_flag_types") or [])
            if f
        }
        gold_flags.discard("")

        try:
            case = CaseInput.model_validate(row)
            out = run_case(case, mode=mode)

            pred_meds = {
                _normalize_med_name(m.name) for m in out.extracted_medications if m.name
            }
            pred_meds.discard("")
            med_pairs.append((pred_meds, gold_meds))

            pred_flags = {
                _normalize_flag_type(f.flag_type) for f in out.risk_flags if f.flag_type
            }
            pred_flags.discard("")
            flag_pairs.append((pred_flags, gold_flags))

            ok += 1
        except Exception as e:
            failed += 1
            if first_error is None:
                first_error = f"row {i}: {type(e).__name__}: {e}"

            # Count failures as empty predictions so gold contributes to FN.
            med_pairs.append((set(), gold_meds))
            flag_pairs.append((set(), gold_flags))

            if failed <= error_print_limit:
                print(
                    f"[{mode}] eval error on row {i}: {type(e).__name__}: {e}",
                    file=sys.stderr,
                )
            elif failed == error_print_limit + 1:
                print(f"[{mode}] additional eval errors omitted", file=sys.stderr)

    med_p, med_r, med_f = micro_prf(med_pairs)
    flag_p, flag_r, flag_f = micro_prf(flag_pairs)
    n = len(rows)
    success_rate = (ok / n) if n else 0.0

    return {
        "n_cases": n,
        "n_ok": ok,
        "n_failed": failed,
        "first_error": first_error,
        "success_rate": success_rate,
        "medication_extraction": {"precision": med_p, "recall": med_r, "f1": med_f},
        "risk_flags": {"precision": flag_p, "recall": flag_r, "f1": flag_f},
    }


def _format_pct(x: float) -> str:
    return f"{x * 100:6.2f}%"


def _print_table(results: dict[str, dict[str, Any]]) -> None:
    header = (
        "mode          ok/total   success   meds_p   meds_r  meds_f1   flags_p  flags_r flags_f1"
    )
    print(header)
    print("-" * len(header))
    for mode in sorted(results.keys()):
        r = results[mode]
        meds = r["medication_extraction"]
        flags = r["risk_flags"]
        print(
            f"{mode:<12} {r.get('n_ok', 0):>3}/{r.get('n_cases', 0):<3} {_format_pct(r['success_rate'])}"
            f" {_format_pct(meds['precision'])} {_format_pct(meds['recall'])}"
            f" {_format_pct(meds['f1'])}"
            f" {_format_pct(flags['precision'])} {_format_pct(flags['recall'])}"
            f" {_format_pct(flags['f1'])}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="medrec-eval")
    parser.add_argument(
        "--data",
        type=str,
        default="data/synth/cases.jsonl",
        help="Path to eval JSONL (default: data/synth/cases.jsonl)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["baseline", "medgemma", "both"],
        default="baseline",
        help="Which mode(s) to evaluate",
    )
    args = parser.parse_args(argv)

    data_path = Path(args.data)
    rows = _read_jsonl(data_path)

    modes = ["baseline"] if args.mode == "baseline" else ["medgemma"]
    if args.mode == "both":
        modes = ["baseline", "medgemma"]

    results: dict[str, dict[str, Any]] = {}
    for mode in modes:
        if mode == "medgemma":
            try:
                results[mode] = _evaluate_mode(mode, rows)
            except Exception as e:
                print(f"Skipping medgemma eval: {e}", file=sys.stderr)
                continue
        else:
            results[mode] = _evaluate_mode(mode, rows)

    out_path = Path("outputs") / "metrics.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")

    _print_table(results)
    print(f"\nwrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
