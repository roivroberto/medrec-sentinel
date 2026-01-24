from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EvidenceSpan(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    start: int
    end: int
    text: str


class Medication(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    name: str
    dose: str | None = None
    route: str | None = None
    frequency: str | None = None
    prn: bool = False
    start: str | None = None
    stop: str | None = None


class RiskFlag(BaseModel):
    model_config = ConfigDict(
        extra="ignore", str_strip_whitespace=True, populate_by_name=True
    )

    flag_type: str = Field(alias="type")
    severity: str
    summary: str
    evidence_spans: list[EvidenceSpan] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)


class CaseInput(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    case_id: str
    discharge_note: str
    known_allergies: list[str] = Field(default_factory=list)
    egfr_ml_min_1_73m2: float | None = None


class PipelineOutput(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    case_id: str
    extracted_medications: list[Medication]
    extracted_allergies: list[str]
    risk_flags: list[RiskFlag]
    pharmacist_note: str
    model_metadata: dict[str, Any]
