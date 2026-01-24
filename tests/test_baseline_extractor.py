from __future__ import annotations


def test_extract_medications_baseline_finds_two_meds() -> None:
    from medrec_sentinel.extract.baseline import extract_medications_baseline

    note = "Discharge meds: lisinopril 10 mg daily; metformin 500mg bid."
    meds = extract_medications_baseline(note)

    names = {m.name for m in meds}
    assert {"lisinopril", "metformin"}.issubset(names)


def test_extract_medications_baseline_empty_note_returns_empty() -> None:
    from medrec_sentinel.extract.baseline import extract_medications_baseline

    assert extract_medications_baseline("") == []


def test_extract_medications_baseline_extracts_dose_and_frequency() -> None:
    from medrec_sentinel.extract.baseline import extract_medications_baseline

    meds = extract_medications_baseline("Discharge meds: lisinopril 10 mg daily")
    assert len(meds) == 1
    assert meds[0].name == "lisinopril"
    assert meds[0].dose == "10 mg"
    assert meds[0].frequency == "daily"


def test_extract_medications_baseline_prn_sets_flag_not_frequency() -> None:
    from medrec_sentinel.extract.baseline import extract_medications_baseline

    meds = extract_medications_baseline("acetaminophen 650 mg prn")
    assert len(meds) == 1
    assert meds[0].name == "acetaminophen"
    assert meds[0].dose == "650 mg"
    assert meds[0].prn is True
    assert meds[0].frequency is None


def test_extract_medications_baseline_avoids_labs_mg_dl() -> None:
    from medrec_sentinel.extract.baseline import extract_medications_baseline

    note = "Labs: glucose 150 mg/dL\nDischarge meds: metformin 500 mg bid"
    meds = extract_medications_baseline(note)

    names = {m.name for m in meds}
    assert names == {"metformin"}


def test_extract_medications_baseline_multi_token_name_stops_at_route() -> None:
    from medrec_sentinel.extract.baseline import extract_medications_baseline

    meds = extract_medications_baseline("sodium chloride flush 10 ml iv daily")
    assert len(meds) == 1
    assert meds[0].name == "sodium chloride flush"
    assert meds[0].route == "iv"


def test_extract_medications_baseline_discharge_meds_splits_commas_and_parses_each() -> None:
    from medrec_sentinel.extract.baseline import extract_medications_baseline

    note = "Discharge meds: warfarin 5 mg daily, ibuprofen 400 mg prn"
    meds = extract_medications_baseline(note)

    names = {m.name for m in meds}
    assert {"warfarin", "ibuprofen"}.issubset(names)
