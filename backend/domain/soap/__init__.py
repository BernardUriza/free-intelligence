"""SOAP domain entities."""

# SOAP models
try:
    from backend.domain.soap.models import SOAPNote, SOAPStatus
except ImportError:
    # Define minimal versions
    from dataclasses import dataclass
    from enum import Enum

    @dataclass
    class SOAPNote:
        subjective: str = ""
        objective: str = ""
        assessment: str = ""
        plan: str = ""

    class SOAPStatus(str, Enum):
        DRAFT = "draft"
        FINAL = "final"

# Repository interface from domain layer (no circular dependency)
from backend.domain.interfaces.isoap_repository import ISOAPRepository

__all__ = [
    "SOAPNote",
    "SOAPStatus",
    "ISOAPRepository",
]
