"""SOAP progression workflow — the note-completeness sub-machine.

Ported faithfully from FLOW.md §3 ("SOAP Progression Workflow") of the
Redux-Claude medical flow. Pure, zero-dep, and **explainable**: given the
structured contents of a SOAP note (Subjective / Objective / Assessment /
Plan), it computes a weighted completeness percentage, per-section sub-scores,
NOM-004 compliance, and whether the note is ready to commit.

This is decision SUPPORT, not diagnosis — it measures *how complete the
documentation is*, never the clinical correctness of its content.

In the consultation state machine this scores the ``SOAP_GENERATION`` →
``READY_TO_COMMIT`` progression (see :mod:`fi_core.cognitive.state_machine`)
and feeds §8 decision point #5 ("Commit SOAP?").

    metrics = calculate_soap_completeness(
        subjective=Subjective(motivo_consulta="chest pain", historia_actual="..."),
        objective=Objective(presion_arterial="120/80", frecuencia_cardiaca=72),
        assessment=Assessment(diagnostico_principal="...",
                              diagnosticos_diferenciales=["a", "b"]),
        plan=Plan(tratamiento_farmacologico="...", seguimiento="..."),
        nom_violations=[],
    )
    print(metrics.percentage, metrics.ready_for_commit)
    print(metrics.sections)  # per-section 0-100 sub-scores
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

#: Overall completeness percentage at or above which a note may commit
#: (FLOW.md §3 ``readyForCommit`` / §8 #5 ``completeness >= 80``).
COMMIT_COMPLETENESS_THRESHOLD = 80

#: NOM-004 compliance score at or above which a note may commit
#: (FLOW.md §3 ``readyForCommit`` / §8 #5 ``nom_compliance >= 90``).
COMMIT_NOM_THRESHOLD = 90


class SOAPSection(str, Enum):
    """The four SOAP sections, in documentation order (FLOW.md §3)."""

    SUBJECTIVE = "subjective"
    OBJECTIVE = "objective"
    ASSESSMENT = "assessment"
    PLAN = "plan"

    @property
    def order(self) -> int:
        """0-based position of this section in the SOAP progression."""
        return _SECTION_ORDER[self]


_SECTION_ORDER: dict[SOAPSection, int] = {
    SOAPSection.SUBJECTIVE: 0,
    SOAPSection.OBJECTIVE: 1,
    SOAPSection.ASSESSMENT: 2,
    SOAPSection.PLAN: 3,
}

#: Section weights for the overall completeness sum (FLOW.md §3 ``WEIGHTS``).
#: They sum to exactly 1.0.
SECTION_WEIGHTS: dict[SOAPSection, float] = {
    SOAPSection.SUBJECTIVE: 0.30,
    SOAPSection.OBJECTIVE: 0.25,
    SOAPSection.ASSESSMENT: 0.25,
    SOAPSection.PLAN: 0.20,
}


@dataclass
class Subjective:
    """The Subjective (S) section — patient-reported information (FLOW.md §3).

    ``medicamentos`` and ``alergias`` model the relevant antecedentes fields.
    """

    motivo_consulta: str = ""
    historia_actual: str = ""
    medicamentos: str = ""
    alergias: str = ""


@dataclass
class Objective:
    """The Objective (O) section — vital signs (FLOW.md §3 ``signosVitales``).

    Each field may be a string or number; emptiness/``None`` means missing.
    """

    presion_arterial: str | None = None
    frecuencia_cardiaca: float | str | None = None
    temperatura: float | str | None = None
    saturacion_oxigeno: float | str | None = None


@dataclass
class Assessment:
    """The Assessment (A) section — diagnostic reasoning (FLOW.md §3)."""

    diagnostico_principal: str = ""
    diagnosticos_diferenciales: list[str] = field(default_factory=list)
    factores_riesgo: str = ""


@dataclass
class Plan:
    """The Plan (P) section — management plan (FLOW.md §3)."""

    tratamiento_farmacologico: str = ""
    seguimiento: str = ""
    estudios_adicionales: str = ""


@dataclass(frozen=True)
class CompletenessMetrics:
    """The result of :func:`calculate_soap_completeness` (FLOW.md §3).

    :attr:`percentage` is the weighted overall completeness (0-100).
    :attr:`sections` maps each :class:`SOAPSection` value to its 0-100
    sub-score. :attr:`nom_compliance` is the NOM-004 score (0-100);
    :attr:`nom_violations` lists the violations behind it.
    :attr:`ready_for_commit` is the §3 gate: overall >= 80 AND nom >= 90.
    """

    percentage: float
    sections: dict[str, float]
    nom_compliance: int
    nom_violations: tuple[str, ...]
    ready_for_commit: bool


def _present(value: object) -> bool:
    """Truthiness as the FLOW.md §3 pseudocode uses it (non-empty / non-None)."""
    return bool(value)


def calculate_soap_completeness(
    subjective: Subjective,
    objective: Objective,
    assessment: Assessment,
    plan: Plan,
    nom_violations: tuple[str, ...] | list[str] = (),
) -> CompletenessMetrics:
    """Calculate SOAP note completeness and NOM-004 compliance (FLOW.md §3).

    Faithful to the ``calculate_soap_completeness`` pseudocode. Per-section
    sub-scores are 0..1, the overall percentage is their weighted sum × 100,
    and NOM-004 compliance is ``max(0, 100 - len(violations) * 10)``. The note
    is ready to commit when overall >= 80 AND nom >= 90.

    ``nom_violations`` is the list of NOM-004 violations (defaulting to empty);
    in production it is produced by an upstream ``check_nom_compliance`` step,
    kept as an input here to preserve this module's zero-dep purity.
    """
    # --- Subjective completeness (0..1) ---
    subjective_score = 0.0
    if _present(subjective.motivo_consulta):
        subjective_score += 0.30
    if _present(subjective.historia_actual):
        subjective_score += 0.30
    if _present(subjective.medicamentos):
        subjective_score += 0.20
    if _present(subjective.alergias):
        subjective_score += 0.20

    # --- Objective completeness (0..1) ---
    objective_score = 0.0
    if _present(objective.presion_arterial):
        objective_score += 0.25
    if _present(objective.frecuencia_cardiaca):
        objective_score += 0.25
    if _present(objective.temperatura):
        objective_score += 0.25
    if _present(objective.saturacion_oxigeno):
        objective_score += 0.25

    # --- Assessment completeness (0..1) ---
    assessment_score = 0.0
    if _present(assessment.diagnostico_principal):
        assessment_score += 0.50
    if len(assessment.diagnosticos_diferenciales) >= 2:
        assessment_score += 0.30
    if _present(assessment.factores_riesgo):
        assessment_score += 0.20

    # --- Plan completeness (0..1) ---
    plan_score = 0.0
    if _present(plan.tratamiento_farmacologico):
        plan_score += 0.40
    if _present(plan.seguimiento):
        plan_score += 0.30
    if _present(plan.estudios_adicionales):
        plan_score += 0.30

    # --- Overall weighted percentage ---
    overall = (
        subjective_score * SECTION_WEIGHTS[SOAPSection.SUBJECTIVE]
        + objective_score * SECTION_WEIGHTS[SOAPSection.OBJECTIVE]
        + assessment_score * SECTION_WEIGHTS[SOAPSection.ASSESSMENT]
        + plan_score * SECTION_WEIGHTS[SOAPSection.PLAN]
    ) * 100

    # --- NOM-004 compliance ---
    violations = tuple(nom_violations)
    nom_score = max(0, 100 - len(violations) * 10)

    return CompletenessMetrics(
        percentage=overall,
        sections={
            SOAPSection.SUBJECTIVE.value: subjective_score * 100,
            SOAPSection.OBJECTIVE.value: objective_score * 100,
            SOAPSection.ASSESSMENT.value: assessment_score * 100,
            SOAPSection.PLAN.value: plan_score * 100,
        },
        nom_compliance=nom_score,
        nom_violations=violations,
        ready_for_commit=(
            overall >= COMMIT_COMPLETENESS_THRESHOLD
            and nom_score >= COMMIT_NOM_THRESHOLD
        ),
    )
