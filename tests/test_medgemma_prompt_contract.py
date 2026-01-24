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


def test_parse_extraction_output_accepts_bare_med_list() -> None:
    from medrec_sentinel.extract.meds import parse_extraction_output

    raw = '[{"name": "amoxicillin", "dose": "500 mg", "frequency": "tid"}]'
    out = parse_extraction_output(raw)

    assert [m.name for m in out.medications] == ["amoxicillin"]


def test_extract_with_medgemma_retries_on_generate_failure(monkeypatch) -> None:
    import medrec_sentinel.llm.medgemma as medgemma
    from medrec_sentinel.extract.meds import extract_with_medgemma

    calls = {"n": 0}

    def fake_generate(_prompt: str, *, max_new_tokens: int, temperature: float) -> str:
        assert max_new_tokens > 0
        assert temperature == 0.0
        calls["n"] += 1
        if calls["n"] == 1:
            raise ValueError("Model output did not contain valid JSON")
        return (
            "{"
            '"medications": [{"name": "lisinopril"}],'
            '"allergies": [],'
            '"egfr_ml_min_1_73m2": null,'
            '"evidence_spans": []'
            "}"
        )

    monkeypatch.setattr(medgemma, "generate", fake_generate)

    out = extract_with_medgemma("Discharge meds: lisinopril 10 mg daily.")
    assert [m.name for m in out.medications] == ["lisinopril"]
    assert calls["n"] == 2
