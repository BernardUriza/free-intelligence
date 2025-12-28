"""Template Engine for medical prescriptions.

Handles template CRUD operations, prescription generation,
and validation logic.

Author: Bernard Uriza Orozco
Created: 2025-12-28
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from backend.src.fi_common.logging.logger import get_logger
from fi_prescription.models.medication import Medication
from fi_prescription.models.prescription import (
    PatientInfo,
    PhysicianInfo,
    Prescription,
    PrescriptionStatus,
)
from fi_prescription.models.template import (
    PrescriptionTemplate,
    get_default_template,
)

logger = get_logger(__name__)


class TemplateEngine:
    """Engine for managing prescription templates and generating prescriptions.

    This is the main service class for the prescription module.
    It handles:
    - Template management (CRUD)
    - Prescription generation from templates
    - Prescription validation
    - Export to various formats

    Attributes:
        templates: In-memory template storage (will be replaced with HDF5/DB)
        prescriptions: In-memory prescription storage
    """

    def __init__(self) -> None:
        """Initialize the template engine with default template."""
        # In-memory storage (to be replaced with persistent storage)
        self._templates: dict[str, PrescriptionTemplate] = {}
        self._prescriptions: dict[str, Prescription] = {}

        # Load default template
        default = get_default_template()
        self._templates[default.id] = default

        logger.info("TEMPLATE_ENGINE_INITIALIZED", template_count=1)

    # =========================================================================
    # Template Management
    # =========================================================================

    def get_template(self, template_id: str) -> Optional[PrescriptionTemplate]:
        """Get a template by ID.

        Args:
            template_id: Template identifier

        Returns:
            Template if found, None otherwise
        """
        return self._templates.get(template_id)

    def get_default_template(self) -> PrescriptionTemplate:
        """Get the default system template.

        Returns:
            Default PrescriptionTemplate
        """
        for template in self._templates.values():
            if template.is_default and template.owner_type == "system":
                return template

        # Fallback: create and store default
        default = get_default_template()
        self._templates[default.id] = default
        return default

    def list_templates(
        self,
        owner_id: Optional[str] = None,
        include_system: bool = True,
    ) -> list[PrescriptionTemplate]:
        """List available templates.

        Args:
            owner_id: Filter by owner (physician/institution)
            include_system: Include system templates

        Returns:
            List of templates matching filters
        """
        templates = []

        for template in self._templates.values():
            if not template.is_active:
                continue

            # Filter by owner
            if owner_id and template.owner_id != owner_id:
                if not (include_system and template.owner_type == "system"):
                    continue

            templates.append(template)

        return sorted(templates, key=lambda t: (not t.is_default, t.name))

    def create_template(
        self,
        template: PrescriptionTemplate,
    ) -> PrescriptionTemplate:
        """Create a new template.

        Args:
            template: Template to create

        Returns:
            Created template with assigned ID
        """
        if not template.id or template.id == "default":
            template.id = str(uuid4())

        template.created_at = datetime.utcnow()
        template.updated_at = datetime.utcnow()

        self._templates[template.id] = template

        logger.info(
            "TEMPLATE_CREATED",
            template_id=template.id,
            name=template.name,
            owner_type=template.owner_type,
        )

        return template

    def update_template(
        self,
        template_id: str,
        updates: dict[str, Any],
    ) -> Optional[PrescriptionTemplate]:
        """Update an existing template.

        Args:
            template_id: Template to update
            updates: Dictionary of fields to update

        Returns:
            Updated template or None if not found
        """
        template = self._templates.get(template_id)
        if not template:
            return None

        # Don't allow modifying system templates directly
        if template.owner_type == "system":
            logger.warning("TEMPLATE_UPDATE_BLOCKED", reason="system template")
            return None

        # Apply updates
        for key, value in updates.items():
            if hasattr(template, key) and key not in ("id", "created_at", "owner_type"):
                setattr(template, key, value)

        template.updated_at = datetime.utcnow()

        logger.info("TEMPLATE_UPDATED", template_id=template_id)

        return template

    def delete_template(self, template_id: str) -> bool:
        """Soft delete a template (mark as inactive).

        Args:
            template_id: Template to delete

        Returns:
            True if deleted, False if not found or system template
        """
        template = self._templates.get(template_id)
        if not template:
            return False

        if template.owner_type == "system":
            logger.warning("TEMPLATE_DELETE_BLOCKED", reason="system template")
            return False

        template.is_active = False
        template.updated_at = datetime.utcnow()

        logger.info("TEMPLATE_DELETED", template_id=template_id)

        return True

    # =========================================================================
    # Prescription Generation
    # =========================================================================

    def create_prescription(
        self,
        template_id: str,
        patient: PatientInfo,
        physician: PhysicianInfo,
        diagnosis: str,
        medications: list[Medication],
        session_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Prescription:
        """Create a new prescription from a template.

        Args:
            template_id: Template to use
            patient: Patient information
            physician: Physician information
            diagnosis: Primary diagnosis
            medications: List of medications
            session_id: Optional session ID
            **kwargs: Additional prescription fields

        Returns:
            Created Prescription

        Raises:
            ValueError: If template not found or validation fails
        """
        template = self.get_template(template_id)
        if not template:
            template = self.get_default_template()

        prescription = Prescription(
            id=str(uuid4()),
            template_id=template.id,
            session_id=session_id,
            status=PrescriptionStatus.DRAFT,
            patient=patient,
            physician=physician,
            diagnosis=diagnosis,
            medications=medications,
            **kwargs,
        )

        # Validate against template
        errors = prescription.validate_completeness()
        if errors:
            logger.warning(
                "PRESCRIPTION_VALIDATION_WARNINGS",
                prescription_id=prescription.id,
                errors=errors,
            )

        self._prescriptions[prescription.id] = prescription

        logger.info(
            "PRESCRIPTION_CREATED",
            prescription_id=prescription.id,
            template_id=template.id,
            medication_count=len(medications),
        )

        return prescription

    def create_prescription_from_soap(
        self,
        soap_data: dict[str, Any],
        patient: PatientInfo,
        physician: PhysicianInfo,
        template_id: str = "default",
        session_id: Optional[str] = None,
    ) -> Prescription:
        """Create a prescription from SOAP note data.

        Extracts diagnosis and treatment from SOAP structure
        and creates a draft prescription.

        Args:
            soap_data: SOAP note dictionary
            patient: Patient information
            physician: Physician information
            template_id: Template to use
            session_id: Session ID for linking

        Returns:
            Created Prescription
        """
        # Extract diagnosis from assessment
        assessment = soap_data.get("assessment", {})
        diagnosis = assessment.get("primary_diagnosis", "")

        # Extract medications from plan
        plan = soap_data.get("plan", {})
        treatment = plan.get("treatment", "")

        # Parse treatment text into medications
        medications = self._parse_medications_from_text(treatment)

        # If no medications parsed, create an empty prescription
        if not medications:
            logger.info(
                "SOAP_NO_MEDICATIONS_PARSED",
                session_id=session_id,
                treatment_text=treatment[:100] if treatment else "",
            )

        return self.create_prescription(
            template_id=template_id,
            patient=patient,
            physician=physician,
            diagnosis=diagnosis,
            medications=medications,
            session_id=session_id,
            general_instructions=plan.get("follow_up", ""),
        )

    def _parse_medications_from_text(self, text: str) -> list[Medication]:
        """Parse medication text into structured Medication objects.

        This is a simplified parser. In production, this would use
        NLP/LLM to extract medication details.

        Args:
            text: Treatment plan text

        Returns:
            List of parsed Medications
        """
        medications: list[Medication] = []

        if not text or not text.strip():
            return medications

        # Simple line-by-line parsing
        lines = text.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Remove common prefixes
            for prefix in ["- ", "• ", "* ", "Rx: ", "Rx ", "1. ", "2. ", "3. "]:
                if line.startswith(prefix):
                    line = line[len(prefix):]
                    break

            # Skip non-medication lines
            skip_keywords = ["seguimiento", "cita", "indicaciones", "reposo", "dieta"]
            if any(kw in line.lower() for kw in skip_keywords):
                continue

            # Try to extract medication name (first word or phrase before dosage)
            # This is simplified - real implementation would use AI
            parts = line.split()
            if parts:
                med_name = parts[0]

                # Look for dosage pattern
                dosage = "según indicación"
                for part in parts[1:]:
                    if any(c.isdigit() for c in part):
                        dosage = part
                        break

                medications.append(
                    Medication(
                        name=med_name,
                        dosage=dosage,
                        instructions=line,  # Store full text as instructions
                    )
                )

        return medications

    # =========================================================================
    # Prescription Operations
    # =========================================================================

    def get_prescription(self, prescription_id: str) -> Optional[Prescription]:
        """Get a prescription by ID.

        Args:
            prescription_id: Prescription identifier

        Returns:
            Prescription if found, None otherwise
        """
        return self._prescriptions.get(prescription_id)

    def list_prescriptions(
        self,
        session_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        physician_id: Optional[str] = None,
        status: Optional[PrescriptionStatus] = None,
        limit: int = 100,
    ) -> list[Prescription]:
        """List prescriptions with optional filters.

        Args:
            session_id: Filter by session
            patient_id: Filter by patient
            physician_id: Filter by physician
            status: Filter by status
            limit: Maximum results

        Returns:
            List of matching prescriptions
        """
        results: list[Prescription] = []

        for rx in self._prescriptions.values():
            if session_id and rx.session_id != session_id:
                continue
            if patient_id and rx.patient.patient_id != patient_id:
                continue
            if physician_id and rx.physician.physician_id != physician_id:
                continue
            if status and rx.status != status:
                continue

            results.append(rx)

            if len(results) >= limit:
                break

        return sorted(results, key=lambda r: r.created_at, reverse=True)

    def update_prescription(
        self,
        prescription_id: str,
        updates: dict[str, Any],
    ) -> Optional[Prescription]:
        """Update a prescription.

        Only draft prescriptions can be updated.

        Args:
            prescription_id: Prescription to update
            updates: Fields to update

        Returns:
            Updated prescription or None
        """
        rx = self._prescriptions.get(prescription_id)
        if not rx:
            return None

        if rx.status != PrescriptionStatus.DRAFT:
            logger.warning(
                "PRESCRIPTION_UPDATE_BLOCKED",
                prescription_id=prescription_id,
                status=rx.status,
            )
            return None

        # Apply updates
        for key, value in updates.items():
            if hasattr(rx, key) and key not in ("id", "created_at", "signature_hash"):
                setattr(rx, key, value)

        logger.info("PRESCRIPTION_UPDATED", prescription_id=prescription_id)

        return rx

    def sign_prescription(self, prescription_id: str) -> Optional[Prescription]:
        """Sign a prescription.

        Args:
            prescription_id: Prescription to sign

        Returns:
            Signed prescription or None
        """
        rx = self._prescriptions.get(prescription_id)
        if not rx:
            return None

        # Validate before signing
        errors = rx.validate_completeness()
        if errors:
            logger.warning(
                "PRESCRIPTION_SIGN_VALIDATION_FAILED",
                prescription_id=prescription_id,
                errors=errors,
            )
            raise ValueError(f"Cannot sign incomplete prescription: {'; '.join(errors)}")

        rx.sign()

        logger.info(
            "PRESCRIPTION_SIGNED",
            prescription_id=prescription_id,
            hash=rx.signature_hash[:16] if rx.signature_hash else None,
        )

        return rx

    def cancel_prescription(
        self,
        prescription_id: str,
        reason: Optional[str] = None,
    ) -> Optional[Prescription]:
        """Cancel a prescription.

        Args:
            prescription_id: Prescription to cancel
            reason: Cancellation reason

        Returns:
            Cancelled prescription or None
        """
        rx = self._prescriptions.get(prescription_id)
        if not rx:
            return None

        rx.cancel(reason)

        logger.info(
            "PRESCRIPTION_CANCELLED",
            prescription_id=prescription_id,
            reason=reason,
        )

        return rx

    def export_to_text(self, prescription_id: str) -> Optional[str]:
        """Export prescription to plain text.

        Args:
            prescription_id: Prescription to export

        Returns:
            Plain text representation or None
        """
        rx = self._prescriptions.get(prescription_id)
        if not rx:
            return None

        return rx.to_print_text()


# Singleton instance
_engine: Optional[TemplateEngine] = None


def get_template_engine() -> TemplateEngine:
    """Get the singleton TemplateEngine instance.

    Returns:
        TemplateEngine instance
    """
    global _engine
    if _engine is None:
        _engine = TemplateEngine()
    return _engine
