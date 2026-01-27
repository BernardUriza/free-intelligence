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

from backend.utils.common.logging.logger import get_logger
from backend.core.domain.prescription.models.allergy import AllergyCheckResult
from backend.core.domain.prescription.models.interaction import InteractionCheckResult
from backend.core.domain.prescription.models.medication import Medication
from backend.core.domain.prescription.models.prescription import (
    PatientInfo,
    PhysicianInfo,
    Prescription,
    PrescriptionStatus,
)
from backend.core.domain.prescription.models.template import (
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

    def get_template(self, template_id: str) -> PrescriptionTemplate | None:
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
        owner_id: str | None = None,
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
    ) -> PrescriptionTemplate | None:
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
        session_id: str | None = None,
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

    def check_interactions(
        self,
        medications: list[Medication],
    ) -> InteractionCheckResult:
        """Check medications for drug-drug interactions.

        Should be called before finalizing a prescription to alert
        the physician of potential interactions.

        Args:
            medications: List of medications to check

        Returns:
            InteractionCheckResult with alerts and recommendations
        """
        from backend.core.domain.prescription.services.interaction_checker import get_interaction_checker

        checker = get_interaction_checker()
        result = checker.check_medication_objects(medications)

        if result.alerts:
            logger.warning(
                "PRESCRIPTION_INTERACTIONS_DETECTED",
                alert_count=len(result.alerts),
                has_major=result.has_major_interactions,
                can_proceed=result.can_proceed,
            )

        return result

    def create_prescription_with_interaction_check(
        self,
        template_id: str,
        patient: PatientInfo,
        physician: PhysicianInfo,
        diagnosis: str,
        medications: list[Medication],
        session_id: str | None = None,
        **kwargs: Any,
    ) -> tuple[Prescription, InteractionCheckResult]:
        """Create a prescription and check for interactions.

        Convenience method that creates the prescription and
        runs interaction checking in one call.

        Args:
            template_id: Template to use
            patient: Patient information
            physician: Physician information
            diagnosis: Primary diagnosis
            medications: List of medications
            session_id: Optional session ID
            **kwargs: Additional prescription fields

        Returns:
            Tuple of (Prescription, InteractionCheckResult)

        Note:
            The prescription is created even if interactions are found.
            The caller should handle the interaction alerts appropriately.
        """
        prescription = self.create_prescription(
            template_id=template_id,
            patient=patient,
            physician=physician,
            diagnosis=diagnosis,
            medications=medications,
            session_id=session_id,
            **kwargs,
        )

        interaction_result = self.check_interactions(medications)

        return prescription, interaction_result

    def check_allergies(
        self,
        medications: list[Medication],
        patient_allergies: list[str],
    ) -> AllergyCheckResult:
        """Check medications against patient allergies.

        Should be called before finalizing a prescription to alert
        the physician of potential allergy issues.

        Args:
            medications: List of medications to check
            patient_allergies: Patient's recorded allergies

        Returns:
            AllergyCheckResult with alerts and recommendations
        """
        from backend.core.domain.prescription.services.allergy_checker import get_allergy_checker

        checker = get_allergy_checker()
        result = checker.check_medication_objects(medications, patient_allergies)

        if result.alerts:
            logger.warning(
                "PRESCRIPTION_ALLERGIES_DETECTED",
                alert_count=len(result.alerts),
                has_severe=result.has_severe_allergies,
                can_proceed=result.can_proceed,
            )

        return result

    def full_safety_check(
        self,
        medications: list[Medication],
        patient_allergies: list[str],
    ) -> dict[str, Any]:
        """Run all safety checks on medications.

        Combines interaction checking and allergy checking into
        a single comprehensive safety report.

        Args:
            medications: List of medications to check
            patient_allergies: Patient's recorded allergies

        Returns:
            Dict with interaction_result, allergy_result, and overall status
        """
        interaction_result = self.check_interactions(medications)
        allergy_result = self.check_allergies(medications, patient_allergies)

        # Determine overall safety
        can_proceed = interaction_result.can_proceed and allergy_result.can_proceed
        has_critical = (
            interaction_result.has_major_interactions or allergy_result.has_severe_allergies
        )

        return {
            "interactions": interaction_result,
            "allergies": allergy_result,
            "can_proceed": can_proceed,
            "has_critical_issues": has_critical,
            "summary": self._generate_safety_summary(
                interaction_result, allergy_result, can_proceed
            ),
        }

    def _generate_safety_summary(
        self,
        interactions: InteractionCheckResult,
        allergies: AllergyCheckResult,
        can_proceed: bool,
    ) -> str:
        """Generate overall safety summary.

        Args:
            interactions: Interaction check result
            allergies: Allergy check result
            can_proceed: Whether prescription can proceed

        Returns:
            Summary message in Spanish
        """
        if not interactions.alerts and not allergies.alerts:
            return "✅ Sin alertas de seguridad. Prescripción puede proceder."

        parts = []
        if interactions.alerts:
            parts.append(f"Interacciones: {len(interactions.alerts)}")
        if allergies.alerts:
            parts.append(f"Alergias: {len(allergies.alerts)}")

        summary = f"⚠️ Alertas detectadas - {', '.join(parts)}."

        if not can_proceed:
            summary += "\n⛔ NO PROCEDER - Revisar alertas críticas antes de prescribir."

        return summary

    def create_prescription_from_soap(
        self,
        soap_data: dict[str, Any],
        patient: PatientInfo,
        physician: PhysicianInfo,
        template_id: str = "default",
        session_id: str | None = None,
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

    def _parse_medications_from_text(
        self,
        text: str,
        use_ai: bool = True,
    ) -> list[Medication]:
        """Parse medication text into structured Medication objects.

        Uses AI (LLM) to extract medications from free text and enriches
        them with data from the Mexico medication catalog.

        Args:
            text: Treatment plan text
            use_ai: Whether to use AI extraction (falls back to simple parser)

        Returns:
            List of parsed Medications with catalog enrichment
        """
        if not text or not text.strip():
            return []

        # Try AI extraction first (FI-RX-003)
        if use_ai:
            try:
                from backend.core.domain.prescription.services.medication_extractor import (
                    get_medication_extractor,
                )

                extractor = get_medication_extractor(provider="ollama")
                medications = extractor.extract_medications(
                    treatment_text=text,
                    enrich_from_catalog=True,
                )

                if medications:
                    logger.info(
                        "MEDICATIONS_EXTRACTED_AI",
                        count=len(medications),
                        medications=[m.name for m in medications],
                    )
                    return medications

            except Exception as e:
                logger.warning(
                    "AI_EXTRACTION_FAILED_FALLBACK",
                    error=str(e),
                )
                # Fall through to simple parsing

        # Fallback: Simple line-by-line parsing
        return self._simple_parse_medications(text)

    def _simple_parse_medications(self, text: str) -> list[Medication]:
        """Simple fallback parser for medications.

        Used when AI extraction is disabled or fails.

        Args:
            text: Treatment plan text

        Returns:
            List of parsed Medications
        """
        medications: list[Medication] = []
        lines = text.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Remove common prefixes
            for prefix in ["- ", "• ", "* ", "Rx: ", "Rx ", "1. ", "2. ", "3. "]:
                if line.startswith(prefix):
                    line = line[len(prefix) :]
                    break

            # Skip non-medication lines
            skip_keywords = ["seguimiento", "cita", "indicaciones", "reposo", "dieta"]
            if any(kw in line.lower() for kw in skip_keywords):
                continue

            # Extract medication name and dosage
            parts = line.split()
            if parts:
                med_name = parts[0]
                dosage = "según indicación"

                for part in parts[1:]:
                    if any(c.isdigit() for c in part):
                        dosage = part
                        break

                medications.append(
                    Medication(
                        name=med_name,
                        dosage=dosage,
                        instructions=line,
                    )
                )

        return medications

    # =========================================================================
    # Prescription Operations
    # =========================================================================

    def get_prescription(self, prescription_id: str) -> Prescription | None:
        """Get a prescription by ID.

        Args:
            prescription_id: Prescription identifier

        Returns:
            Prescription if found, None otherwise
        """
        return self._prescriptions.get(prescription_id)

    def list_prescriptions(
        self,
        session_id: str | None = None,
        patient_id: str | None = None,
        physician_id: str | None = None,
        status: PrescriptionStatus | None = None,
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
    ) -> Prescription | None:
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

    def sign_prescription(self, prescription_id: str) -> Prescription | None:
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
        reason: str | None = None,
    ) -> Prescription | None:
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

    def export_to_text(self, prescription_id: str) -> str | None:
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
_engine: TemplateEngine | None = None


def get_template_engine() -> TemplateEngine:
    """Get the singleton TemplateEngine instance.

    Returns:
        TemplateEngine instance
    """
    global _engine
    if _engine is None:
        _engine = TemplateEngine()
    return _engine
