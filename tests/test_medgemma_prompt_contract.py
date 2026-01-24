from __future__ import annotations


def test_parse_extraction_output_contract_smoke() -> None:
    from medrec_sentinel.extract.meds import parse_extraction_output

    raw = '{"medications": [{"name": "lisinopril", "dose": "10 mg", "frequency": "daily"}], "allergies": ["penicillin"], "egfr_ml_min_1_73m2": 42.0}'
    out = parse_extraction_output(raw)

    assert out.medications[0].name == "lisinopril"
    assert out.allergies == ["penicillin"]


def test_parse_extraction_output_parses_fenced_json() -> None:
    from medrec_sentinel.extract.meds import parse_extraction_output

    raw = (
        "```json\n"
        '{"medications": [{"name": "metformin"}], "allergies": [], "egfr_ml_min_1_73m2": null}\n'
        "```"
    )
    out = parse_extraction_output(raw)

    assert out.medications[0].name == "metformin"


def test_parse_extraction_output_parses_json_with_leading_text() -> None:
    from medrec_sentinel.extract.meds import parse_extraction_output

    raw = (
        "Here is the extracted JSON:\n"
        '{"medications": [], "allergies": ["latex"], "egfr_ml_min_1_73m2": 55.0}\n'
        "Thanks."
    )
    out = parse_extraction_output(raw)

    assert out.allergies == ["latex"]
