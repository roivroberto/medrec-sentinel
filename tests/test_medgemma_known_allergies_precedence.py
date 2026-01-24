from __future__ import annotations


def test_medgemma_known_allergies_empty_list_overrides_extracted(monkeypatch) -> None:
    import importlib

    run_case_mod = importlib.import_module("medrec_sentinel.pipeline.run_case")

    from medrec_sentinel.extract.meds import ExtractionResult
    from medrec_sentinel.schemas import CaseInput, Medication

    def fake_extract_with_medgemma(_note: str) -> ExtractionResult:
        return ExtractionResult(
            medications=[Medication(name="acetaminophen")],
            allergies=["penicillin"],
            egfr_ml_min_1_73m2=60.0,
        )

    monkeypatch.setattr(run_case_mod, "extract_with_medgemma", fake_extract_with_medgemma)

    case = CaseInput(
        case_id="case_001",
        discharge_note="Discharge meds: acetaminophen.",
        known_allergies=[],
        egfr_ml_min_1_73m2=None,
    )
    out = run_case_mod.run_case(case, mode="medgemma")

    assert out.extracted_allergies == []


def test_medgemma_known_allergies_omitted_uses_extracted(monkeypatch) -> None:
    import importlib

    run_case_mod = importlib.import_module("medrec_sentinel.pipeline.run_case")

    from medrec_sentinel.extract.meds import ExtractionResult
    from medrec_sentinel.schemas import CaseInput, Medication

    def fake_extract_with_medgemma(_note: str) -> ExtractionResult:
        return ExtractionResult(
            medications=[Medication(name="acetaminophen")],
            allergies=["penicillin"],
            egfr_ml_min_1_73m2=60.0,
        )

    monkeypatch.setattr(run_case_mod, "extract_with_medgemma", fake_extract_with_medgemma)

    case = CaseInput.model_validate(
        {
            "case_id": "case_001",
            "discharge_note": "Discharge meds: acetaminophen.",
        }
    )
    assert "known_allergies" not in case.model_fields_set

    out = run_case_mod.run_case(case, mode="medgemma")
    assert out.extracted_allergies == ["penicillin"]


def test_medgemma_egfr_explicit_none_overrides_extracted(monkeypatch) -> None:
    import importlib

    run_case_mod = importlib.import_module("medrec_sentinel.pipeline.run_case")

    from medrec_sentinel.extract.meds import ExtractionResult
    from medrec_sentinel.schemas import CaseInput, Medication

    def fake_extract_with_medgemma(_note: str) -> ExtractionResult:
        return ExtractionResult(
            medications=[Medication(name="acetaminophen")],
            allergies=[],
            egfr_ml_min_1_73m2=60.0,
        )

    captured: dict[str, object] = {}

    def fake_run_risk_checks(
        _meds: list[Medication],
        _allergies: list[str],
        egfr: float | None,
    ) -> list[object]:
        captured["egfr"] = egfr
        return []

    monkeypatch.setattr(run_case_mod, "extract_with_medgemma", fake_extract_with_medgemma)
    monkeypatch.setattr(run_case_mod, "run_risk_checks", fake_run_risk_checks)

    case = CaseInput(
        case_id="case_001",
        discharge_note="Discharge meds: acetaminophen.",
        known_allergies=[],
        egfr_ml_min_1_73m2=None,
    )
    assert "egfr_ml_min_1_73m2" in case.model_fields_set

    run_case_mod.run_case(case, mode="medgemma")

    assert captured["egfr"] is None
