"""SOAP Complexity Analyzer - Determines if case needs multi-persona orchestration.

Philosophy: Not all SOAP cases are created equal. Simple consultations (fever, checkup)
need 1 LLM call. Complex cases (multiple diagnoses, comorbidities, treatment plans)
need orchestrated fine-tuning with multiple expert personas.

File: backend/services/soap_generation/complexity_analyzer.py
Created: 2025-11-20
Pattern: Strategy Pattern + Heuristic Analysis
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ComplexityMetrics:
    """Metrics that determine SOAP case complexity."""

    # Text metrics
    word_count: int
    speaker_turn_count: int
    unique_medical_terms: int

    # Clinical metrics
    diagnosis_count: int
    symptom_count: int
    medication_count: int
    comorbidity_mentioned: bool

    # Structural metrics
    has_physical_exam: bool
    has_lab_results: bool
    has_imaging: bool

    # Derived
    complexity_score: float = 0.0
    complexity_level: str = "UNKNOWN"  # SIMPLE, MODERATE, COMPLEX, CRITICAL

    def __post_init__(self) -> None:
        """Calculate complexity score and level."""
        self.complexity_score = self._calculate_score()
        self.complexity_level = self._determine_level()

    def _calculate_score(self) -> float:
        """
        Calculate complexity score (0-100).

        Heuristics:
        - Long transcript = more complex
        - Multiple turns = detailed discussion
        - Many medical terms = specialized vocabulary
        - Multiple diagnoses = complex case
        - Comorbidities = higher complexity
        - Lab/imaging = objective data to process
        """
        score = 0.0

        # Text length (0-20 points)
        if self.word_count > 1000:
            score += 20
        elif self.word_count > 500:
            score += 15
        elif self.word_count > 200:
            score += 10
        else:
            score += 5

        # Speaker turns (0-15 points)
        if self.speaker_turn_count > 20:
            score += 15
        elif self.speaker_turn_count > 10:
            score += 10
        else:
            score += 5

        # Medical vocabulary (0-15 points)
        score += min(self.unique_medical_terms * 1.5, 15)

        # Clinical complexity (0-30 points)
        score += min(self.diagnosis_count * 10, 20)
        score += min(self.symptom_count * 2, 10)

        # Comorbidities (0-10 points)
        if self.comorbidity_mentioned:
            score += 10

        # Objective data (0-10 points)
        if self.has_lab_results:
            score += 5
        if self.has_imaging:
            score += 5

        return min(score, 100.0)

    def _determine_level(self) -> str:
        """Determine complexity level from score."""
        if self.complexity_score >= 75:
            return "CRITICAL"  # Needs multi-persona orchestration + doctor validation
        elif self.complexity_score >= 50:
            return "COMPLEX"   # Needs multi-persona orchestration
        elif self.complexity_score >= 25:
            return "MODERATE"  # Single persona with review
        else:
            return "SIMPLE"    # Single persona, direct generation


class ComplexityAnalyzer:
    """
    Analyzes SOAP case complexity to determine generation strategy.

    Strategy Selection:
    - SIMPLE: Single LLM call (soap_generator preset)
    - MODERATE: Single call + clinical_advisor review
    - COMPLEX: Multi-persona orchestration (soap_editor → clinical_advisor → soap_editor)
    - CRITICAL: Full orchestration + request doctor context
    """

    # Medical terminology indicators (expandable)
    MEDICAL_TERMS = {
        # Diagnoses
        "diabetes", "hipertensión", "insuficiencia", "cardíaca", "renal", "hepática",
        "crónica", "aguda", "oncológico", "cáncer", "tumor", "metástasis",

        # Symptoms/Signs
        "disnea", "taquicardia", "bradicardia", "hipotensión", "hipertensión",
        "fiebre", "cefalea", "náusea", "vómito", "diarrea", "estreñimiento",

        # Medications
        "metformina", "insulina", "enalapril", "losartán", "atorvastatina",
        "omeprazol", "paracetamol", "ibuprofeno", "amoxicilina",

        # Lab/Imaging
        "glucosa", "hemoglobina", "creatinina", "radiografía", "tomografía",
        "resonancia", "ultrasonido", "electrocardiograma", "ecocardiograma",
    }

    def __init__(self) -> None:
        self.logger = get_logger(__name__)

    def analyze(
        self,
        transcript: str,
        segments: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ComplexityMetrics:
        """
        Analyze SOAP case complexity.

        Args:
            transcript: Full medical conversation transcript
            segments: Optional diarization segments (for speaker turn analysis)
            metadata: Optional session metadata (prior context)

        Returns:
            ComplexityMetrics with scores and recommended strategy
        """
        transcript_lower = transcript.lower()

        # Text metrics
        words = transcript.split()
        word_count = len(words)
        speaker_turn_count = len(segments) if segments else self._estimate_turns(transcript)

        # Medical vocabulary
        unique_medical_terms = len([
            term for term in self.MEDICAL_TERMS
            if term in transcript_lower
        ])

        # Clinical indicators (heuristic keyword matching)
        diagnosis_count = self._count_diagnoses(transcript_lower)
        symptom_count = self._count_symptoms(transcript_lower)
        medication_count = self._count_medications(transcript_lower)
        comorbidity_mentioned = self._detect_comorbidity(transcript_lower)

        # Structural elements
        has_physical_exam = self._has_physical_exam(transcript_lower)
        has_lab_results = self._has_lab_results(transcript_lower)
        has_imaging = self._has_imaging(transcript_lower)

        metrics = ComplexityMetrics(
            word_count=word_count,
            speaker_turn_count=speaker_turn_count,
            unique_medical_terms=unique_medical_terms,
            diagnosis_count=diagnosis_count,
            symptom_count=symptom_count,
            medication_count=medication_count,
            comorbidity_mentioned=comorbidity_mentioned,
            has_physical_exam=has_physical_exam,
            has_lab_results=has_lab_results,
            has_imaging=has_imaging,
        )

        self.logger.info(
            "COMPLEXITY_ANALYSIS_COMPLETE",
            score=metrics.complexity_score,
            level=metrics.complexity_level,
            word_count=word_count,
            diagnosis_count=diagnosis_count,
        )

        return metrics

    def _estimate_turns(self, transcript: str) -> int:
        """Estimate speaker turns from transcript (if no diarization)."""
        # Heuristic: Count lines or paragraph breaks
        lines = [line.strip() for line in transcript.split('\n') if line.strip()]
        return len(lines)

    def _count_diagnoses(self, transcript: str) -> int:
        """Count potential diagnoses mentioned."""
        diagnosis_indicators = [
            "diagnóstico", "diagnosis", "padece", "sufre de", "tiene",
            "diabetes", "hipertensión", "insuficiencia", "cáncer",
        ]
        count = sum(1 for indicator in diagnosis_indicators if indicator in transcript)
        return min(count, 5)  # Cap at 5 to avoid over-counting

    def _count_symptoms(self, transcript: str) -> int:
        """Count symptoms mentioned."""
        symptom_keywords = [
            "dolor", "fiebre", "tos", "náusea", "vómito", "diarrea",
            "cefalea", "mareo", "debilidad", "fatiga", "disnea",
        ]
        count = sum(1 for symptom in symptom_keywords if symptom in transcript)
        return min(count, 10)

    def _count_medications(self, transcript: str) -> int:
        """Count medications mentioned."""
        medication_keywords = [
            "medicamento", "toma", "prescrib", "receta",
            "metformina", "insulina", "enalapril", "losartán",
        ]
        count = sum(1 for med in medication_keywords if med in transcript)
        return min(count, 8)

    def _detect_comorbidity(self, transcript: str) -> bool:
        """Detect if multiple comorbid conditions mentioned."""
        comorbidity_indicators = [
            "también padece", "además tiene", "comorbilidad",
            "múltiples condiciones", "antecedentes de",
        ]
        return any(indicator in transcript for indicator in comorbidity_indicators)

    def _has_physical_exam(self, transcript: str) -> bool:
        """Detect if physical exam findings mentioned."""
        exam_keywords = [
            "exploración física", "examen físico", "auscultación",
            "palpación", "presión arterial", "frecuencia cardíaca",
            "temperatura", "peso", "talla", "imc",
        ]
        return any(keyword in transcript for keyword in exam_keywords)

    def _has_lab_results(self, transcript: str) -> bool:
        """Detect if lab results mentioned."""
        lab_keywords = [
            "laboratorio", "análisis", "glucosa", "hemoglobina",
            "creatinina", "colesterol", "triglicéridos", "hba1c",
        ]
        return any(keyword in transcript for keyword in lab_keywords)

    def _has_imaging(self, transcript: str) -> bool:
        """Detect if imaging studies mentioned."""
        imaging_keywords = [
            "radiografía", "rayos x", "tomografía", "tac", "resonancia",
            "rm", "ultrasonido", "ecografía", "ecocardiograma",
        ]
        return any(keyword in transcript for keyword in imaging_keywords)


# ============================================================================
# GLOBAL ANALYZER INSTANCE (Singleton)
# ============================================================================

_analyzer: ComplexityAnalyzer | None = None


def get_complexity_analyzer() -> ComplexityAnalyzer:
    """Get or create global complexity analyzer instance."""
    global _analyzer

    if _analyzer is None:
        _analyzer = ComplexityAnalyzer()

    return _analyzer
