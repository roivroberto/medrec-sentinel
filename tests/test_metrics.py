import importlib
import importlib.util


def test_f1_plan_example_rounds_to_point8() -> None:
    try:
        spec = importlib.util.find_spec("medrec_sentinel.eval.metrics")
    except ModuleNotFoundError:
        spec = None
    assert spec is not None

    metrics = importlib.import_module("medrec_sentinel.eval.metrics")
    assert hasattr(metrics, "f1")

    p, r, f = metrics.f1(tp=8, fp=2, fn=2)
    assert round(p, 2) == 0.80
    assert round(r, 2) == 0.80
    assert round(f, 2) == 0.80


def test_f1_all_zero_is_zero() -> None:
    metrics = importlib.import_module("medrec_sentinel.eval.metrics")
    p, r, f = metrics.f1(tp=0, fp=0, fn=0)
    assert (p, r, f) == (0.0, 0.0, 0.0)


def test_prf_from_sets_basic() -> None:
    metrics = importlib.import_module("medrec_sentinel.eval.metrics")
    p, r, f = metrics.prf_from_sets(pred={"a", "b"}, gold={"b", "c"})
    assert round(p, 2) == 0.50
    assert round(r, 2) == 0.50
    assert round(f, 2) == 0.50


def test_micro_prf_sums_counts_not_mean() -> None:
    metrics = importlib.import_module("medrec_sentinel.eval.metrics")
    pairs = [
        ({"a"}, {"a", "b"}),
        (set(), {"c"}),
    ]
    p, r, f = metrics.micro_prf(pairs)
    assert round(p, 2) == 1.00
    assert round(r, 2) == 0.33
    assert round(f, 2) == 0.50
