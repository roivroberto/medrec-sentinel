from __future__ import annotations

import argparse
import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

GENERATOR_VERSION = "synth-2"


@dataclass(frozen=True)
class MedLine:
    name: str
    dose: str
    route: str
    frequency: str
    prn: bool = False


def _choice(rng: random.Random, xs: list[str]) -> str:
    return xs[rng.randrange(len(xs))]


def _maybe(rng: random.Random, p: float) -> bool:
    return rng.random() < p


def _freq_variant(rng: random.Random, canonical: str) -> str:
    # Intentional formatting/noise variants.
    variants = {
        "daily": ["daily", "qd", "qday", "QDAY", "every day"],
        "bid": ["BID", "bid", "q12h", "twice daily", "2x/day"],
        "tid": ["TID", "tid", "q8h", "three times daily"],
        "prn": ["PRN", "prn", "as needed", "as needed (PRN)"],
        "hs": ["HS", "qhs", "at bedtime"],
    }
    return _choice(rng, variants.get(canonical, [canonical]))


def _format_med_line(rng: random.Random, med: MedLine) -> str:
    name = med.name
    if _maybe(rng, 0.35):
        name = name.upper() if _maybe(rng, 0.5) else name.title()

    freq = med.frequency
    if _maybe(rng, 0.6):
        freq = _freq_variant(rng, freq)

    pieces: list[str] = [name, med.dose]

    if _maybe(rng, 0.8):
        pieces.append(med.route)

    # Insert some spacing/punctuation noise.
    if _maybe(rng, 0.3):
        pieces.append("-")

    pieces.append(freq)
    if med.prn and "prn" not in freq.lower():
        pieces.append(_freq_variant(rng, "prn"))

    line = " ".join(pieces)
    if _maybe(rng, 0.25):
        line = line.replace(" ", "  ")
    if _maybe(rng, 0.25):
        line = line.replace("-", ":")
    return line.strip()


def _render_note(
    rng: random.Random,
    *,
    case_id: str,
    allergies: list[str],
    egfr: float | None,
    meds: list[MedLine],
) -> str:
    header = _choice(
        rng,
        [
            "DISCHARGE SUMMARY",
            "Discharge Summary",
            "DISCHARGE NOTE",
            "Discharge Note",
        ],
    )

    patient = _choice(rng, ["J. Doe", "M. Smith", "A. Johnson", "R. Patel", "K. Nguyen"])
    age = rng.randrange(22, 89)
    sex = _choice(rng, ["M", "F"])

    lines: list[str] = [header, "", f"Case: {case_id}", f"Patient: {patient} ({age}{sex})"]

    # Allergies section with variants.
    if allergies:
        if _maybe(rng, 0.5):
            lines.append(f"Allergies: {', '.join(allergies)}")
        else:
            lines.append("Allergies/Intolerances")
            for a in allergies:
                bullet = _choice(rng, ["-", "*", "o"])
                lines.append(f"{bullet} {a}")
    else:
        lines.append(_choice(rng, ["Allergies: NKDA", "Allergies: none known"]))

    # Labs snippet.
    if egfr is not None:
        if _maybe(rng, 0.5):
            lines.append(f"Renal: eGFR {egfr:.0f} mL/min/1.73m2")
        else:
            lines.append(f"Labs: Cr stable; eGFR~{egfr:.0f}")

    # Med list.
    lines.append("")
    lines.append(_choice(rng, ["Discharge Medications:", "DISCHARGE MEDS:", "Meds on discharge:"]))

    list_style = _choice(rng, ["bullets", "numbers", "inline"])
    if list_style == "inline":
        med_chunks = [_format_med_line(rng, m) for m in meds]
        lines.append("; ".join(med_chunks))
    elif list_style == "numbers":
        for i, m in enumerate(meds, start=1):
            lines.append(f"{i}. {_format_med_line(rng, m)}")
    else:
        for m in meds:
            bullet = _choice(rng, ["-", "*", "-"])
            lines.append(f"{bullet} {_format_med_line(rng, m)}")

    # Instructions with noise.
    lines.append("")
    if _maybe(rng, 0.5):
        lines.append(_choice(rng, ["Follow up with PCP in 1-2 weeks.", "F/U: PCP 1-2 wks."]))
    if _maybe(rng, 0.35):
        lines.append(_choice(rng, ["Return precautions reviewed.", "ER precautions discussed."]))

    # Random extra whitespace.
    if _maybe(rng, 0.2):
        lines.insert(1, " ")

    return "\n".join(lines).rstrip() + "\n"


def _stable_case_seed(seed: int, case_id: str) -> int:
    h = hashlib.blake2b(digest_size=8)
    h.update(str(seed).encode("utf-8"))
    h.update(b":")
    h.update(case_id.encode("utf-8"))
    return int.from_bytes(h.digest(), "big", signed=False)


def _seed_scenario(case_id: str, which: str) -> dict[str, Any]:
    # Scenario definitions (canonical med names in gold_med_names).
    if which == "allergy_conflict":
        allergies = ["penicillin"]
        egfr = None
        meds = [
            MedLine("amoxicillin", "500 mg", "PO", "tid"),
            MedLine("acetaminophen", "650 mg", "PO", "prn", prn=True),
        ]
        expected_meds = ["amoxicillin", "acetaminophen"]
    elif which == "duplication":
        allergies = []
        egfr = None
        meds = [
            MedLine("lisinopril", "10 mg", "PO", "daily"),
            MedLine("benazepril", "10 mg", "PO", "daily"),
        ]
        expected_meds = ["lisinopril", "benazepril"]
    elif which == "renal_risk":
        allergies = []
        egfr = 25.0
        meds = [
            MedLine("metformin", "1000 mg", "PO", "bid"),
            MedLine("insulin glargine", "10 units", "SC", "hs"),
        ]
        expected_meds = ["metformin", "insulin glargine"]
    elif which == "bleed_risk":
        allergies = []
        egfr = None
        meds = [
            MedLine("warfarin", "5 mg", "PO", "daily"),
            MedLine("ibuprofen", "400 mg", "PO", "prn", prn=True),
        ]
        expected_meds = ["warfarin", "ibuprofen"]
    else:
        raise ValueError(f"unknown scenario: {which}")

    return {
        "case_id": case_id,
        "known_allergies": allergies,
        "egfr_ml_min_1_73m2": egfr,
        "gold_med_names": expected_meds,
        "gold_flag_types": [which],
        "scenario": which,
        "_meds": meds,
    }


def _random_case(rng: random.Random, case_id: str) -> dict[str, Any]:
    common_meds = [
        MedLine("atorvastatin", "40 mg", "PO", "hs"),
        MedLine("amlodipine", "5 mg", "PO", "daily"),
        MedLine("metoprolol succinate", "50 mg", "PO", "daily"),
        MedLine("omeprazole", "20 mg", "PO", "daily"),
        MedLine("albuterol", "2 puffs", "INH", "prn", prn=True),
        MedLine("sertraline", "50 mg", "PO", "daily"),
        MedLine("furosemide", "20 mg", "PO", "daily"),
        MedLine("gabapentin", "300 mg", "PO", "tid"),
        MedLine("acetaminophen", "650 mg", "PO", "prn", prn=True),
    ]

    allergies_pool = [
        "shellfish",
        "latex",
        "sulfa",
        "penicillin",
        "codeine",
    ]

    allergies: list[str] = []
    if _maybe(rng, 0.45):
        allergies = rng.sample(allergies_pool, k=1 if _maybe(rng, 0.8) else 2)

    egfr: float | None = None
    if _maybe(rng, 0.25):
        egfr = float(rng.randrange(18, 95))

    meds = rng.sample(common_meds, k=rng.randrange(3, 7))
    expected_meds = [m.name for m in meds]

    gold_flag_types: list[str] = []
    # Occasionally sprinkle in a known risk pattern to keep evaluation signal.
    if _maybe(rng, 0.08):
        gold_flag_types.append("bleed_risk")
        meds.append(MedLine("warfarin", "5 mg", "PO", "daily"))
        meds.append(MedLine(_choice(rng, ["ibuprofen", "naproxen"]), "400 mg", "PO", "prn", prn=True))
        expected_meds.extend(["warfarin", meds[-1].name])

    return {
        "case_id": case_id,
        "known_allergies": allergies,
        "egfr_ml_min_1_73m2": egfr,
        "gold_med_names": expected_meds,
        "gold_flag_types": gold_flag_types,
        "scenario": "random",
        "_meds": meds,
    }


def generate_cases(n: int, seed: int) -> list[dict[str, Any]]:
    scenarios = ["allergy_conflict", "duplication", "renal_risk", "bleed_risk"]
    out: list[dict[str, Any]] = []
    for i in range(n):
        case_id = f"synth-{seed}-{i:04d}"
        rng = random.Random(_stable_case_seed(seed, case_id))
        if i < len(scenarios):
            rec = _seed_scenario(case_id, scenarios[i])
        else:
            rec = _random_case(rng, case_id)

        discharge_note = _render_note(
            rng,
            case_id=rec["case_id"],
            allergies=rec["known_allergies"],
            egfr=rec["egfr_ml_min_1_73m2"],
            meds=rec.pop("_meds"),
        )
        rec["discharge_note"] = discharge_note
        rec["generator_seed"] = seed
        rec["generator_version"] = GENERATOR_VERSION
        out.append(rec)

    return out


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Generate synthetic discharge-note cases")
    p.add_argument("--n", type=int, default=200)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", type=Path, default=Path("data/synth/cases.jsonl"))
    args = p.parse_args(argv)

    rows = generate_cases(n=args.n, seed=args.seed)
    _write_jsonl(args.out, rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
