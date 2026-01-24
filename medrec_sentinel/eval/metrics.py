from __future__ import annotations

from collections.abc import Iterable


def f1(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    """Return (precision, recall, f1) from counts.

    The behavior is intentionally simple for eval harness usage.
    """

    if tp < 0 or fp < 0 or fn < 0:
        raise ValueError("tp/fp/fn must be >= 0")

    p_denom = tp + fp
    r_denom = tp + fn
    precision = (tp / p_denom) if p_denom else 0.0
    recall = (tp / r_denom) if r_denom else 0.0

    f_denom = precision + recall
    f1_score = (2.0 * precision * recall / f_denom) if f_denom else 0.0
    return precision, recall, f1_score


def prf_from_sets(pred: set[str], gold: set[str]) -> tuple[float, float, float]:
    tp = len(pred & gold)
    fp = len(pred - gold)
    fn = len(gold - pred)
    return f1(tp=tp, fp=fp, fn=fn)


def micro_prf(pairs: Iterable[tuple[set[str], set[str]]]) -> tuple[float, float, float]:
    tp = fp = fn = 0
    for pred, gold in pairs:
        tp += len(pred & gold)
        fp += len(pred - gold)
        fn += len(gold - pred)
    return f1(tp=tp, fp=fp, fn=fn)
