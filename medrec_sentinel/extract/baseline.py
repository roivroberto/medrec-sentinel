from __future__ import annotations

import re

from medrec_sentinel.schemas import Medication

_DOSE_RE = re.compile(
    r"(?P<amt>\d+(?:\.\d+)?)\s*(?P<unit>mg|mcg|g|unit(?:s)?|iu|ml)\b(?!\s*/\s*d\s*l\b)",
    re.IGNORECASE,
)

_FREQ_TOKENS = [
    "daily",
    "qd",
    "qday",
    "bid",
    "tid",
    "qhs",
]

_ROUTE_TOKENS = [
    "po",
    "iv",
    "im",
    "sc",
    "sq",
    "subq",
    "sl",
    "pr",
    "inhaled",
    "topical",
    "nasal",
    "ophthalmic",
    "otic",
]

_NAME_STOP_TOKENS = set(_FREQ_TOKENS) | set(_ROUTE_TOKENS) | {
    "prn",
    "as",
    "needed",
    "for",
    "take",
    "tablet",
    "tablets",
    "tab",
    "tabs",
    "capsule",
    "capsules",
    "cap",
    "caps",
    "by",
    "mouth",
}


def _parse_medication_chunk(chunk: str, *, allow_name_only: bool) -> Medication | None:
    chunk = chunk.strip()
    if not chunk:
        return None

    low = chunk.lower()

    prn = bool(re.search(r"\bprn\b", low))

    route: str | None = None
    for tok in _ROUTE_TOKENS:
        if re.search(rf"\b{re.escape(tok)}\b", low):
            route = tok
            break

    dose_match = _DOSE_RE.search(chunk)
    dose: str | None = None
    if dose_match:
        amt = dose_match.group("amt")
        unit = dose_match.group("unit").lower()
        dose = f"{amt} {unit}"

    frequency: str | None = None
    for tok in _FREQ_TOKENS:
        if re.search(rf"\b{re.escape(tok)}\b", low):
            frequency = tok
            break

    if not allow_name_only and not (dose_match or frequency or route or prn):
        return None

    # Heuristic drug name: everything before the first dose match; otherwise up
    # to three tokens.
    name_part = chunk
    if dose_match:
        name_part = chunk[: dose_match.start()]
    name_part = name_part.lower()
    name_part = re.sub(r"[^a-z0-9\s-]", " ", name_part)
    name_part = re.sub(r"\s+", " ", name_part).strip(" -")
    if not name_part:
        return None

    name_tokens: list[str] = []
    for tok in name_part.split():
        if tok in _NAME_STOP_TOKENS:
            break
        name_tokens.append(tok)
        if len(name_tokens) == 3:
            break
    if not name_tokens:
        return None
    name = " ".join(name_tokens)

    return Medication(
        name=name,
        dose=dose,
        route=route,
        frequency=frequency,
        prn=prn,
    )


def extract_medications_baseline(note: str) -> list[Medication]:
    """Very small heuristic medication extractor.

    Goal: provide a deterministic baseline for the pipeline. This is not intended
    to be clinically complete.
    """

    meds: list[Medication] = []
    if not note.strip():
        return meds

    for raw_chunk in re.split(r"[;\n]+", note):
        raw_chunk = raw_chunk.strip()
        if not raw_chunk:
            continue

        is_discharge_meds_line = bool(
            re.match(r"^\s*discharge\s+meds\s*:\s*", raw_chunk, flags=re.I)
        )

        # Strip common section labels.
        chunk = re.sub(r"^\s*discharge\s+meds\s*:\s*", "", raw_chunk, flags=re.I)
        if not chunk.strip():
            continue

        # For an explicit discharge meds line we always split on commas and
        # parse each segment independently (supports both name-only and
        # dose/frequency/PRN segments).
        if is_discharge_meds_line:
            for part in chunk.split(","):
                med = _parse_medication_chunk(part, allow_name_only=True)
                if med is not None:
                    meds.append(med)
            continue

        med = _parse_medication_chunk(chunk, allow_name_only=False)
        if med is not None:
            meds.append(med)

    return meds
