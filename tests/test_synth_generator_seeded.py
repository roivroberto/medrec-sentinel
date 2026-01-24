from __future__ import annotations

import json

import scripts.generate_synth_cases as gen


def test_generate_cases_deterministic_seed() -> None:
    a = gen.generate_cases(n=25, seed=123)
    b = gen.generate_cases(n=25, seed=123)

    # Full structural determinism.
    assert a == b

    for row in a:
        # Rows should be directly JSON-serializable.
        json.dumps(row)

        # Internal generation-only fields should never persist.
        assert "_meds" not in row
        assert "_scenario" not in row

        # Persisted labels should avoid leading underscores.
        assert "scenario" in row
        assert "gold_med_names" in row
        assert "gold_flag_types" in row
        assert "generator_seed" in row
        assert row["generator_seed"] == 123
