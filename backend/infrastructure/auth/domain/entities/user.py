from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class UserRole(str, Enum):
    """MVP role enum — only 2 roles: superadmin and clinician."""

    SUPERADMIN = "FI-superadmin"
    CLINICIAN = "FI-clinician"

    @classmethod
    def coerce(cls, raw: str | None) -> UserRole | None:
        if not raw:
            return None

        normalized = str(raw).strip()
        try:
            return cls(normalized)
        except ValueError:
            fallback_map = {
                "medico": cls.CLINICIAN,
                "enfermera": cls.CLINICIAN,
                "fi-admin": cls.CLINICIAN,
                "fi-doctor": cls.CLINICIAN,
                "fi-nurse": cls.CLINICIAN,
                "fi-staff": cls.CLINICIAN,
                "fi-patient": cls.CLINICIAN,
                "fi-viewer": cls.CLINICIAN,
                "admin": cls.SUPERADMIN,
                "superadmin": cls.SUPERADMIN,
                "fi-superadmin": cls.SUPERADMIN,
            }
            mapped = fallback_map.get(normalized.lower())
            return mapped


@dataclass
class User:
    id: str
    email: str
    roles: list[UserRole] = field(default_factory=list)
    tenant_id: str | None = None
    clinic_id: str | None = None  # Multi-tenancy: extracted from JWT claims
    metadata: dict[str, Any] = field(default_factory=dict)
    name: str | None = None
    username: str | None = None

    @property
    def user_id(self) -> str:
        return self.id

    @property
    def sub(self) -> str:
        return self.id

    @property
    def primary_role(self) -> UserRole | None:
        return self.roles[0] if self.roles else None

    @property
    def role(self) -> UserRole | None:
        return self.primary_role

    @property
    def permissions(self) -> set[str]:
        perms = self.metadata.get("permissions")
        if isinstance(perms, Iterable) and not isinstance(perms, (str, bytes)):
            return {str(p) for p in perms}
        return set()
