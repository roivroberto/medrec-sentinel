from __future__ import annotations

import re

from medrec_sentinel.rules.knowledge_base import KB, Rule
from medrec_sentinel.schemas import Medication, RiskFlag

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def _normalize_free_text(value: str) -> str:
    value = value.lower()
    value = _NON_ALNUM_RE.sub(" ", value)
    return " ".join(value.split())


def _tokenize(value: str) -> set[str]:
    norm = _normalize_free_text(value)
    if not norm:
        return set()
    return set(norm.split(" "))


def _term_matches_tokens(term: str, tokens: set[str]) -> bool:
    norm = _normalize_free_text(term)
    if not norm:
        return False
    return set(norm.split(" ")).issubset(tokens)


def _rule_matches(
    *,
    rule: Rule,
    med_tokens: set[str],
    allergy_tokens: set[str],
    egfr_ml_min_1_73m2: float | None,
) -> bool:
    if rule.requires_meds_all and not all(
        _term_matches_tokens(m, med_tokens) for m in rule.requires_meds_all
    ):
        return False

    if rule.requires_meds_any and not any(
        _term_matches_tokens(m, med_tokens) for m in rule.requires_meds_any
    ):
        return False

    if rule.requires_meds_groups_all:
        for group in rule.requires_meds_groups_all:
            if not any(_term_matches_tokens(m, med_tokens) for m in group):
                return False

    if rule.requires_allergy_any and not any(
        _term_matches_tokens(a, allergy_tokens) for a in rule.requires_allergy_any
    ):
        return False

    if rule.egfr_lt is not None:
        if egfr_ml_min_1_73m2 is None:
            return False
        if not (egfr_ml_min_1_73m2 < rule.egfr_lt):
            return False

    return True


def run_risk_checks(
    meds: list[Medication],
    allergies: list[str],
    egfr_ml_min_1_73m2: float | None,
) -> list[RiskFlag]:
    """Deterministic risk flags from curated KB rules."""

    med_tokens: set[str] = set()
    for med in meds:
        med_tokens.update(_tokenize(med.name))

    allergy_tokens: set[str] = set()
    for allergy in allergies:
        allergy_tokens.update(_tokenize(allergy))

    out: list[RiskFlag] = []
    for rule in KB.rules:
        if not _rule_matches(
            rule=rule,
            med_tokens=med_tokens,
            allergy_tokens=allergy_tokens,
            egfr_ml_min_1_73m2=egfr_ml_min_1_73m2,
        ):
            continue

        out.append(
            RiskFlag(
                flag_type=rule.flag_type,
                severity=rule.severity,
                summary=rule.summary,
                citations=list(rule.citations),
                evidence_spans=[],
            )
        )

    return out
