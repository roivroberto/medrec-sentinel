from __future__ import annotations


def test_risk_engine_smoke_warfarin_plus_ibuprofen_bleed_risk() -> None:
    from medrec_sentinel.rules.engine import run_risk_checks
    from medrec_sentinel.schemas import Medication

    flags = run_risk_checks(
        meds=[Medication(name="warfarin"), Medication(name="ibuprofen")],
        allergies=[],
        egfr_ml_min_1_73m2=None,
    )

    assert any(f.flag_type == "bleed_risk" for f in flags)


def test_risk_engine_penicillin_allergy_amoxicillin() -> None:
    from medrec_sentinel.rules.engine import run_risk_checks
    from medrec_sentinel.schemas import Medication

    flags = run_risk_checks(
        meds=[Medication(name="amoxicillin")],
        allergies=["penicillin"],
        egfr_ml_min_1_73m2=None,
    )

    assert any(f.flag_type == "allergy_conflict" for f in flags)


def test_risk_engine_metformin_low_egfr() -> None:
    from medrec_sentinel.rules.engine import run_risk_checks
    from medrec_sentinel.schemas import Medication

    flags = run_risk_checks(
        meds=[Medication(name="metformin")],
        allergies=[],
        egfr_ml_min_1_73m2=25.0,
    )

    assert any(f.flag_type == "renal_risk" for f in flags)


def test_risk_engine_duplicate_acei_lisinopril_benazepril() -> None:
    from medrec_sentinel.rules.engine import run_risk_checks
    from medrec_sentinel.schemas import Medication

    flags = run_risk_checks(
        meds=[Medication(name="lisinopril"), Medication(name="benazepril")],
        allergies=[],
        egfr_ml_min_1_73m2=None,
    )

    assert any(f.flag_type == "duplication" for f in flags)


def test_risk_engine_grouped_requirements_acei_plus_arb_dual_blockade() -> None:
    from medrec_sentinel.rules.engine import run_risk_checks
    from medrec_sentinel.schemas import Medication

    flags = run_risk_checks(
        meds=[Medication(name="lisinopril"), Medication(name="losartan")],
        allergies=[],
        egfr_ml_min_1_73m2=None,
    )

    assert any(f.flag_type == "duplication" for f in flags)


def test_risk_engine_triple_whammy_hyphenated_combo_name() -> None:
    from medrec_sentinel.rules.engine import run_risk_checks
    from medrec_sentinel.schemas import Medication

    flags = run_risk_checks(
        meds=[
            Medication(name="lisinopril-hydrochlorothiazide"),
            Medication(name="ibuprofen"),
        ],
        allergies=[],
        egfr_ml_min_1_73m2=None,
    )

    assert any(f.flag_type == "renal_risk" for f in flags)


def test_risk_engine_metformin_rule_requires_egfr_value() -> None:
    from medrec_sentinel.rules.engine import run_risk_checks
    from medrec_sentinel.schemas import Medication

    flags = run_risk_checks(
        meds=[Medication(name="metformin")],
        allergies=[],
        egfr_ml_min_1_73m2=None,
    )

    assert not any(f.flag_type == "renal_risk" for f in flags)


def test_term_matching_requires_all_tokens_in_term() -> None:
    from medrec_sentinel.rules.engine import _rule_matches, _tokenize
    from medrec_sentinel.rules.knowledge_base import Rule

    rule = Rule(
        rule_id="test_multi_token_term",
        flag_type="test",
        severity="low",
        summary="test",
        requires_meds_any=("lisinopril hydrochlorothiazide",),
    )

    assert _rule_matches(
        rule=rule,
        med_tokens=_tokenize("lisinopril-hydrochlorothiazide"),
        allergy_tokens=set(),
        egfr_ml_min_1_73m2=None,
    )
