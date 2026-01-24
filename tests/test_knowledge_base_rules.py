from __future__ import annotations

from medrec_sentinel.rules import knowledge_base as kb


def test_kb_contains_required_rule_ids() -> None:
    rule_ids = {r.rule_id for r in kb.KB.rules}
    assert "ddi_warfarin_nsaid" in rule_ids


def test_rule_ids_unique() -> None:
    rule_ids = [r.rule_id for r in kb.KB.rules]
    assert len(rule_ids) == len(set(rule_ids))


def test_rule_flag_type_and_severity_allowed() -> None:
    allowed_flag_types = {
        "allergy_conflict",
        "duplication",
        "renal_risk",
        "bleed_risk",
    }
    allowed_severity = {"high", "moderate"}

    for rule in kb.KB.rules:
        assert rule.rule_id
        assert rule.flag_type in allowed_flag_types
        assert rule.severity in allowed_severity


def test_combo_rules_have_expected_group_counts() -> None:
    rules = {r.rule_id: r for r in kb.KB.rules}

    assert len(rules["ddi_acei_arb_dual_ras_blockade"].requires_meds_groups_all) == 2
    assert len(rules["bleed_risk_ssri_nsaid"].requires_meds_groups_all) == 2
    assert (
        len(rules["renal_acei_diuretic_nsaid_triple_whammy"].requires_meds_groups_all)
        == 3
    )
    assert (
        len(
            rules[
                "bleed_risk_dual_antiplatelet_or_anticoagulant"
            ].requires_meds_groups_all
        )
        == 2
    )
    assert len(rules["dup_opioid_benzo"].requires_meds_groups_all) == 2
