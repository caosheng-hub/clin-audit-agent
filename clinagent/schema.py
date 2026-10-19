from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class CheckType(str, Enum):
    RANGE = "range"
    REQUIRED = "required"
    DATE_ORDER = "date_order"
    VISIT_WINDOW = "visit_window"
    CONSISTENCY = "consistency"
    CONMED_PROHIBITED = "conmed_prohibited"


class Rule(BaseModel):
    rule_id: str
    trial_id: str
    code: str
    domain: str
    field: str | None = None
    check_type: CheckType
    params: dict[str, Any] = Field(default_factory=dict)
    severity: Severity = Severity.MAJOR
    description: str
    section_id: str
    section_title: str
    quote: str


class Anomaly(BaseModel):
    anomaly_id: str
    subject_id: str
    rule_id: str
    domain: str
    field: str | None = None
    expected: str
    actual: str
    severity: Severity
    check_type: CheckType
    evidence: str = ""


class GroundTruthAnomaly(BaseModel):
    anomaly_id: str
    subject_id: str
    rule_id: str
    domain: str
    field: str | None = None
    expected: str
    actual: str
    severity: Severity
    anomaly_type: str
    injected: bool = True
