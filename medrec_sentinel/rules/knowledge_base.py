from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Rule:
    rule_id: str
    flag_type: str
    severity: str
    summary: str
    citations: tuple[str, ...] = ()

    # Optional machine-readable criteria for deterministic matching.
    requires_allergy_any: tuple[str, ...] = ()
    requires_meds_all: tuple[str, ...] = ()
    requires_meds_any: tuple[str, ...] = ()
    # Each nested tuple is an "OR" group; all groups must be satisfied.
    requires_meds_groups_all: tuple[tuple[str, ...], ...] = ()
    egfr_lt: float | None = None


@dataclass(frozen=True, slots=True)
class KnowledgeBase:
    rules: tuple[Rule, ...]


NSAIDS: tuple[str, ...] = (
    "ibuprofen",
    "naproxen",
    "diclofenac",
    "indomethacin",
    "ketorolac",
    "meloxicam",
    "celecoxib",
)

ACEIS: tuple[str, ...] = (
    "lisinopril",
    "benazepril",
    "enalapril",
    "ramipril",
)

ARBS: tuple[str, ...] = (
    "losartan",
    "valsartan",
    "irbesartan",
    "candesartan",
)

ACE_OR_ARB: tuple[str, ...] = ACEIS + ARBS

DIURETICS: tuple[str, ...] = (
    "furosemide",
    "hydrochlorothiazide",
    "chlorthalidone",
    "bumetanide",
)

SSRIs_SNRIs: tuple[str, ...] = (
    "sertraline",
    "fluoxetine",
    "paroxetine",
    "citalopram",
    "escitalopram",
    "venlafaxine",
    "duloxetine",
)

ANTICOAGULANTS: tuple[str, ...] = (
    "warfarin",
    "apixaban",
    "rivaroxaban",
    "dabigatran",
    "heparin",
    "enoxaparin",
)

ANTIPLATELETS: tuple[str, ...] = (
    "aspirin",
    "clopidogrel",
)

OPIOIDS: tuple[str, ...] = (
    "oxycodone",
    "hydrocodone",
    "morphine",
    "hydromorphone",
    "fentanyl",
    "tramadol",
)

BENZOS: tuple[str, ...] = (
    "lorazepam",
    "diazepam",
    "alprazolam",
    "clonazepam",
)


# Keep this small, high-impact, and deterministic. Curate for common inpatient
# discharge-med reconciliation hazards.
KB = KnowledgeBase(
    rules=(
        Rule(
            rule_id="allergy_penicillin_amoxicillin",
            flag_type="allergy_conflict",
            severity="high",
            summary="Penicillin allergy documented; amoxicillin is a penicillin-class antibiotic.",
            citations=(
                "Amoxicillin (FDA label): contraindicated in patients with history of allergic reaction to any penicillin.",
                "Joint Task Force Practice Parameter: Drug allergy (beta-lactam hypersensitivity) guidance.",
            ),
            requires_allergy_any=("penicillin",),
            requires_meds_any=("amoxicillin",),
        ),
        Rule(
            rule_id="dup_acei_lisinopril_benazepril",
            flag_type="duplication",
            severity="high",
            summary="Duplicate ACE inhibitor therapy (lisinopril + benazepril) increases risk of hypotension, AKI, and hyperkalemia.",
            citations=(
                "KDIGO CKD guideline: avoid unnecessary dual RAS blockade due to AKI/hyperkalemia risk.",
                "ACC/AHA hypertension guidance: use a single ACE inhibitor rather than duplicate agents.",
            ),
            requires_meds_all=("lisinopril", "benazepril"),
        ),
        Rule(
            rule_id="renal_metformin_egfr_lt_30",
            flag_type="renal_risk",
            severity="high",
            summary="Metformin is contraindicated at eGFR < 30 mL/min/1.73m2 due to lactic acidosis risk.",
            citations=(
                "Metformin (FDA label): contraindicated in patients with eGFR below 30 mL/min/1.73m2.",
                "ADA Standards of Care: metformin not recommended when eGFR < 30.",
            ),
            requires_meds_any=("metformin",),
            egfr_lt=30.0,
        ),
        Rule(
            rule_id="ddi_warfarin_nsaid",
            flag_type="bleed_risk",
            severity="high",
            summary="Warfarin plus NSAID increases bleeding risk (platelet inhibition/GI injury) even if INR unchanged.",
            citations=(
                "Warfarin (FDA label): concomitant NSAIDs may increase risk of bleeding.",
                "ACG guideline on GI bleeding prevention: NSAIDs increase GI bleed risk; risk is higher with anticoagulants.",
            ),
            requires_meds_all=("warfarin",),
            requires_meds_any=NSAIDS,
        ),
        Rule(
            rule_id="renal_nsaid_egfr_lt_30",
            flag_type="renal_risk",
            severity="high",
            summary="Avoid routine NSAID use in advanced CKD (eGFR < 30) due to AKI and CKD progression risk.",
            citations=(
                "KDIGO CKD guideline: NSAIDs can precipitate AKI; avoid in advanced CKD when possible.",
            ),
            requires_meds_any=NSAIDS,
            egfr_lt=30.0,
        ),
        Rule(
            rule_id="ddi_acei_arb_dual_ras_blockade",
            flag_type="duplication",
            severity="high",
            summary="Dual RAS blockade (ACE inhibitor + ARB) increases risk of hyperkalemia and AKI without routine benefit.",
            citations=(
                "ONTARGET trial: increased renal events/hyperkalemia with ACEi+ARB vs monotherapy.",
                "KDIGO CKD guideline: avoid dual ACEi/ARB in most patients.",
            ),
            requires_meds_groups_all=(ACEIS, ARBS),
        ),
        Rule(
            rule_id="bleed_risk_ssri_nsaid",
            flag_type="bleed_risk",
            severity="moderate",
            summary="SSRI/SNRI plus NSAID increases GI bleeding risk; consider gastroprotection or alternatives.",
            citations=(
                "Systematic reviews: combined SSRI and NSAID therapy increases upper GI bleeding risk.",
            ),
            requires_meds_groups_all=(SSRIs_SNRIs, NSAIDS),
        ),
        Rule(
            rule_id="renal_acei_diuretic_nsaid_triple_whammy",
            flag_type="renal_risk",
            severity="high",
            summary="ACEi/ARB + diuretic + NSAID (triple whammy) increases AKI risk.",
            citations=(
                "Drug safety literature: triple therapy (ACEi/ARB, diuretic, NSAID) associated with increased AKI.",
            ),
            requires_meds_groups_all=(ACE_OR_ARB, DIURETICS, NSAIDS),
        ),
        Rule(
            rule_id="bleed_risk_dual_antiplatelet_or_anticoagulant",
            flag_type="bleed_risk",
            severity="high",
            summary="Multiple agents affecting hemostasis (anticoagulant plus antiplatelet) increase bleeding risk; verify indication and duration.",
            citations=(
                "ACC/AHA guidance: combination antithrombotic therapy increases bleeding; minimize duration when possible.",
            ),
            requires_meds_groups_all=(ANTICOAGULANTS, ANTIPLATELETS),
        ),
        Rule(
            rule_id="dup_opioid_benzo",
            flag_type="duplication",
            severity="high",
            summary="Opioid plus benzodiazepine increases risk of respiratory depression and overdose.",
            citations=(
                "FDA boxed warning: concomitant opioids and benzodiazepines can cause profound sedation, respiratory depression, coma, and death.",
                "CDC opioid guideline: avoid co-prescribing opioids and benzodiazepines when possible.",
            ),
            requires_meds_groups_all=(OPIOIDS, BENZOS),
        ),
        Rule(
            rule_id="renal_dose_gabapentin_low_egfr",
            flag_type="renal_risk",
            severity="moderate",
            summary="Gabapentin requires renal dose adjustment; accumulation can cause sedation and dizziness.",
            citations=(
                "Gabapentin (FDA label): dosage should be adjusted in patients with reduced renal function.",
            ),
            requires_meds_any=("gabapentin",),
            egfr_lt=60.0,
        ),
    )
)
