"""Decisional Middleware - Intelligent SOAP generation orchestration.

NOT an HTTP middleware! This is a SERVICE LAYER middleware (Redux pattern).
Intercepts SOAP generation requests, analyzes complexity, decides strategy.

Philosophy: Intelligence isn't about more compute - it's about right compute.
Simple cases get fast single-pass. Complex cases get multi-persona orchestration.

Strategies:
- SIMPLE: soap_generator (1 call)
- MODERATE: soap_generator + clinical_advisor review (2 calls)
- COMPLEX: soap_editor → clinical_advisor → soap_editor refinement (3 calls)
- CRITICAL: Full orchestration + request doctor context (4+ calls)

File: backend/services/soap_generation/decisional_middleware.py
Created: 2025-11-20
Pattern: Redux Middleware + Chain of Responsibility
"""

from __future__ import annotations

from dataclasses import dataclass
from backend.compat import UTC, datetime
from typing import Any

from backend.logger import get_logger
from backend.providers.llm import llm_generate
from backend.schemas.preset_loader import get_preset_loader
from backend.services.llm.persona_manager import PersonaManager
from backend.services.soap_generation.complexity_analyzer import (
    ComplexityMetrics,
    get_complexity_analyzer,
)

logger = get_logger(__name__)


@dataclass
class OrchestrationPlan:
    """Plan for SOAP generation based on complexity analysis."""

    complexity_metrics: ComplexityMetrics
    strategy: str  # SIMPLE, MODERATE, COMPLEX, CRITICAL
    personas: list[str]  # Ordered list of personas to invoke
    estimated_duration_seconds: int
    requires_doctor_context: bool
    reasoning: str

    def __post_init__(self) -> None:
        """Validate orchestration plan."""
        if not self.personas:
            raise ValueError("OrchestrationPlan must have at least one persona")


@dataclass
class OrchestrationResult:
    """Result of multi-persona SOAP orchestration."""

    soap_note: dict[str, Any]
    strategy_used: str
    personas_invoked: list[str]
    total_duration_seconds: float
    intermediate_outputs: list[dict[str, Any]]  # For debugging/audit
    doctor_context_requested: bool
    confidence_score: float  # 0-1, how confident the model is


class DecisionalMiddleware:
    """
    Intelligent SOAP generation orchestrator.

    Redux Middleware Pattern:
    1. Intercept SOAP generation request
    2. Analyze complexity (complexity_analyzer)
    3. Plan orchestration strategy (decide personas)
    4. Execute orchestration (invoke personas in sequence)
    5. Return result

    Does NOT:
    - Handle HTTP (that's the router's job)
    - Access HDF5 directly (that's repository's job)
    - Make clinical decisions (only orchestration)
    """

    def __init__(self) -> None:
        self.logger = get_logger(__name__)
        self.complexity_analyzer = get_complexity_analyzer()
        self.persona_manager = PersonaManager()
        self.preset_loader = get_preset_loader()

    def process(
        self,
        transcript: str,
        segments: list[dict[str, Any]] | None = None,
        session_metadata: dict[str, Any] | None = None,
    ) -> OrchestrationResult:
        """
        Main orchestration method.

        Args:
            transcript: Full medical conversation
            segments: Optional diarization segments
            session_metadata: Optional session context

        Returns:
            OrchestrationResult with SOAP note and execution details
        """
        start_time = datetime.now(UTC)

        self.logger.info(
            "DECISIONAL_MIDDLEWARE_START",
            transcript_length=len(transcript),
            has_segments=segments is not None,
        )

        # Step 1: Analyze complexity
        metrics = self.complexity_analyzer.analyze(
            transcript=transcript,
            segments=segments,
            metadata=session_metadata,
        )

        # Step 2: Plan orchestration strategy
        plan = self._plan_orchestration(metrics)

        self.logger.info(
            "ORCHESTRATION_PLAN_CREATED",
            strategy=plan.strategy,
            personas=plan.personas,
            estimated_duration=plan.estimated_duration_seconds,
            reasoning=plan.reasoning,
        )

        # Step 3: Execute orchestration
        result = self._execute_orchestration(plan, transcript)

        # Step 4: Calculate metrics
        duration = (datetime.now(UTC) - start_time).total_seconds()
        result.total_duration_seconds = duration

        self.logger.info(
            "DECISIONAL_MIDDLEWARE_COMPLETE",
            strategy=result.strategy_used,
            duration_seconds=duration,
            confidence=result.confidence_score,
        )

        return result

    def _plan_orchestration(self, metrics: ComplexityMetrics) -> OrchestrationPlan:
        """
        Plan orchestration strategy based on complexity metrics.

        Strategy Decision Tree:
        - SIMPLE (score < 25): soap_generator only
        - MODERATE (score 25-49): soap_generator + clinical_advisor review
        - COMPLEX (score 50-74): Multi-pass refinement
        - CRITICAL (score >= 75): Full orchestration + doctor context request
        """
        level = metrics.complexity_level
        score = metrics.complexity_score

        if level == "SIMPLE":
            return OrchestrationPlan(
                complexity_metrics=metrics,
                strategy="SIMPLE",
                personas=["soap_generator"],
                estimated_duration_seconds=8,
                requires_doctor_context=False,
                reasoning="Low complexity case - single-pass generation sufficient",
            )

        elif level == "MODERATE":
            return OrchestrationPlan(
                complexity_metrics=metrics,
                strategy="MODERATE",
                personas=["soap_generator", "clinical_advisor"],
                estimated_duration_seconds=15,
                requires_doctor_context=False,
                reasoning="Moderate complexity - generate + clinical review for accuracy",
            )

        elif level == "COMPLEX":
            return OrchestrationPlan(
                complexity_metrics=metrics,
                strategy="COMPLEX",
                personas=["soap_editor", "clinical_advisor", "soap_editor"],
                estimated_duration_seconds=25,
                requires_doctor_context=False,
                reasoning="High complexity - multi-pass refinement with clinical validation",
            )

        else:  # CRITICAL
            return OrchestrationPlan(
                complexity_metrics=metrics,
                strategy="CRITICAL",
                personas=["soap_editor", "clinical_advisor", "soap_editor", "clinical_advisor"],
                estimated_duration_seconds=40,
                requires_doctor_context=True,
                reasoning="Critical complexity - full orchestration + request additional doctor context",
            )

    def _execute_orchestration(
        self,
        plan: OrchestrationPlan,
        transcript: str,
    ) -> OrchestrationResult:
        """
        Execute multi-persona orchestration.

        Flow (for COMPLEX strategy):
        1. soap_editor: Generate initial draft
        2. clinical_advisor: Review for medical accuracy, suggest improvements
        3. soap_editor: Refine based on feedback

        Returns:
            OrchestrationResult with final SOAP note
        """
        intermediate_outputs = []
        current_content = transcript
        final_soap_note = {}

        for i, persona_name in enumerate(plan.personas):
            step_num = i + 1
            total_steps = len(plan.personas)

            self.logger.info(
                "ORCHESTRATION_STEP_START",
                step=step_num,
                total_steps=total_steps,
                persona=persona_name,
            )

            # Build prompt based on orchestration stage
            if persona_name == "soap_generator":
                # Standard SOAP generation
                prompt = self._build_soap_generation_prompt(current_content)
                output = self._invoke_persona_with_preset(
                    persona_name="soap_generator",
                    preset_name="soap_generator",
                    prompt=prompt,
                )

            elif persona_name == "soap_editor":
                if step_num == 1:
                    # Initial draft generation
                    prompt = self._build_soap_editor_initial_prompt(current_content)
                else:
                    # Refinement based on clinical feedback
                    feedback = intermediate_outputs[-1].get("output", {})
                    prompt = self._build_soap_editor_refinement_prompt(
                        transcript=current_content,
                        previous_draft=final_soap_note,
                        clinical_feedback=feedback,
                    )

                output = self._invoke_persona(
                    persona_name="soap_editor",
                    prompt=prompt,
                )

            elif persona_name == "clinical_advisor":
                # Clinical review/validation
                previous_soap = intermediate_outputs[-1].get("output", {})
                prompt = self._build_clinical_advisor_prompt(
                    transcript=current_content,
                    soap_draft=previous_soap,
                )
                output = self._invoke_persona(
                    persona_name="clinical_advisor",
                    prompt=prompt,
                )

            else:
                raise ValueError(f"Unknown persona: {persona_name}")

            # Store intermediate result
            intermediate_outputs.append({
                "step": step_num,
                "persona": persona_name,
                "output": output,
                "timestamp": datetime.now(UTC).isoformat(),
            })

            # Update final SOAP note if this is a generation step
            if persona_name in ["soap_generator", "soap_editor"]:
                final_soap_note = output

            self.logger.info(
                "ORCHESTRATION_STEP_COMPLETE",
                step=step_num,
                persona=persona_name,
            )

        # Calculate confidence score based on strategy
        confidence = self._calculate_confidence(plan.strategy, final_soap_note)

        return OrchestrationResult(
            soap_note=final_soap_note,
            strategy_used=plan.strategy,
            personas_invoked=plan.personas,
            total_duration_seconds=0.0,  # Will be set by caller
            intermediate_outputs=intermediate_outputs,
            doctor_context_requested=plan.requires_doctor_context,
            confidence_score=confidence,
        )

    def _invoke_persona_with_preset(
        self,
        persona_name: str,
        preset_name: str,
        prompt: str,
    ) -> dict[str, Any]:
        """Invoke persona using preset configuration."""
        try:
            preset = self.preset_loader.load_preset(preset_name)

            full_prompt = f"{preset.system_prompt}\n\n{prompt}"

            response = llm_generate(
                full_prompt,
                temperature=preset.temperature,
                max_tokens=preset.max_tokens,
            )

            # Try to parse as JSON (SOAP note)
            import json
            try:
                return json.loads(response.content)
            except json.JSONDecodeError:
                # Return as text if not JSON
                return {"raw_output": response.content}

        except Exception as e:
            self.logger.error(
                "PERSONA_INVOCATION_FAILED",
                persona=persona_name,
                preset=preset_name,
                error=str(e),
            )
            raise

    def _invoke_persona(self, persona_name: str, prompt: str) -> dict[str, Any]:
        """Invoke persona using PersonaManager (without preset)."""
        persona_config = self.persona_manager.get_persona(persona_name)

        full_prompt = f"{persona_config.system_prompt}\n\n{prompt}"

        response = llm_generate(
            full_prompt,
            temperature=persona_config.temperature,
            max_tokens=persona_config.max_tokens,
        )

        # Try to parse as JSON
        import json
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            return {"raw_output": response.content}

    def _build_soap_generation_prompt(self, transcript: str) -> str:
        """Build prompt for standard SOAP generation."""
        return f"""Generate a SOAP note from this medical conversation:

{transcript}

Extract:
- Subjective: Patient's chief complaint and symptoms
- Objective: Physical exam findings, vital signs, lab results
- Assessment: Diagnosis and clinical reasoning
- Plan: Treatment plan, medications, follow-up

Return JSON format matching soap.schema.json."""

    def _build_soap_editor_initial_prompt(self, transcript: str) -> str:
        """Build prompt for initial SOAP draft."""
        return f"""You are a medical documentation specialist. Create a detailed SOAP note from this conversation:

{transcript}

Focus on:
- Accurate medical terminology
- Complete symptom documentation
- Clear clinical reasoning
- Specific treatment plans

Return JSON format."""

    def _build_soap_editor_refinement_prompt(
        self,
        transcript: str,
        previous_draft: dict[str, Any],
        clinical_feedback: dict[str, Any],
    ) -> str:
        """Build prompt for refining SOAP based on clinical feedback."""
        return f"""Refine this SOAP note based on clinical advisor feedback:

Original Transcript:
{transcript}

Previous Draft:
{previous_draft}

Clinical Feedback:
{clinical_feedback}

Improve:
- Address all clinical concerns raised
- Ensure medical accuracy
- Maintain comprehensive documentation

Return refined JSON."""

    def _build_clinical_advisor_prompt(
        self,
        transcript: str,
        soap_draft: dict[str, Any],
    ) -> str:
        """Build prompt for clinical review."""
        return f"""Review this SOAP note for medical accuracy and completeness:

Original Transcript:
{transcript}

SOAP Note Draft:
{soap_draft}

Provide:
1. Clinical accuracy assessment
2. Missing information
3. Recommended improvements
4. Red flags or concerns

Return JSON with feedback."""

    def _calculate_confidence(self, strategy: str, soap_note: dict[str, Any]) -> float:
        """Calculate confidence score based on strategy and completeness."""
        base_confidence = {
            "SIMPLE": 0.85,
            "MODERATE": 0.90,
            "COMPLEX": 0.95,
            "CRITICAL": 0.98,
        }.get(strategy, 0.80)

        # Adjust based on completeness
        has_subjective = bool(soap_note.get("subjective"))
        has_objective = bool(soap_note.get("objective"))
        has_assessment = bool(soap_note.get("assessment"))
        has_plan = bool(soap_note.get("plan"))

        completeness = sum([has_subjective, has_objective, has_assessment, has_plan]) / 4
        final_confidence = base_confidence * completeness

        return round(final_confidence, 2)


# ============================================================================
# GLOBAL MIDDLEWARE INSTANCE (Singleton)
# ============================================================================

_middleware: DecisionalMiddleware | None = None


def get_decisional_middleware() -> DecisionalMiddleware:
    """Get or create global decisional middleware instance."""
    global _middleware

    if _middleware is None:
        _middleware = DecisionalMiddleware()

    return _middleware
