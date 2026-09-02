"""Modelos de datos para resultados de validación."""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Severity(str, Enum):
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
    location: Optional[str] = None
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
