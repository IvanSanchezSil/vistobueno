"""Modelos de datos para resultados de validación."""

from dataclasses import dataclass
from enum import StrEnum


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass
class RuleResult:
    rule_id: str
    passed: bool
    severity: Severity
    message: str
    expected: str = ""
    found: str = ""
    location: str | None = None
    fuente: str = ""
    cita: str = ""

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "passed": self.passed,
            "severity": self.severity.value,
            "message": self.message,
            "expected": self.expected,
            "found": self.found,
            "location": self.location,
            "fuente": self.fuente,
            "cita": self.cita,
        }
