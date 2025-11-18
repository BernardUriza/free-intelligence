"""
Widget Configurations API - AURITY

Serves configurable widget data (trivia, breathing exercises, daily tips)
from JSON config files instead of hardcoded values.

This enables doctors to add/edit widget content without code changes.

Card: FI-TV-REFAC-002

Author: Bernard Uriza Orozco
Created: 2025-11-18
"""

import json
import random
from pathlib import Path
from typing import Any, List, Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Config file paths
CONFIG_PATH = Path("config/tv_widgets")
TRIVIA_CONFIG = CONFIG_PATH / "trivia.json"
BREATHING_CONFIG = CONFIG_PATH / "breathing.json"
TIPS_CONFIG = CONFIG_PATH / "daily_tips.json"


# ============================================================================
# Pydantic Schemas (Validation)
# ============================================================================


class TriviaQuestion(BaseModel):
    """Trivia question schema with validation."""

    id: str = Field(..., description="Unique question ID")
    question: str = Field(..., min_length=10, description="Question text")
    options: List[str] = Field(..., min_length=2, max_length=6, description="Answer options")
    correct: int = Field(..., ge=0, description="Index of correct answer")
    explanation: str = Field(..., min_length=10, description="Explanation of correct answer")
    difficulty: Literal["easy", "medium", "hard"] = Field(default="medium")
    category: str = Field(..., description="Question category")
    tags: List[str] = Field(default_factory=list, description="Search tags")


class BreathingPhase(BaseModel):
    """Single phase of breathing exercise."""

    phase: Literal["inhale", "hold", "exhale"] = Field(..., description="Breathing phase type")
    duration: int = Field(..., gt=0, le=30, description="Duration in seconds")
    label: str = Field(..., description="Display label for phase")
    icon: str = Field(..., description="Icon to display")
    color: Literal["cyan", "purple", "orange", "green", "blue"] = Field(
        ..., description="Color theme"
    )


class BreathingExercise(BaseModel):
    """Breathing exercise schema with pattern."""

    id: str = Field(..., description="Unique exercise ID")
    name: str = Field(..., description="Exercise name")
    description: str = Field(..., description="Exercise description")
    pattern: List[BreathingPhase] = Field(..., min_length=2, description="Breathing pattern phases")
    total_duration: int = Field(..., gt=0, description="Total cycle duration in seconds")
    benefits: List[str] = Field(..., description="Health benefits")
    difficulty: Literal["beginner", "intermediate", "advanced"] = Field(default="beginner")


class HealthTip(BaseModel):
    """Daily health tip schema."""

    id: str = Field(..., description="Unique tip ID")
    tip: str = Field(..., min_length=20, description="Tip content")
    icon: str = Field(..., description="Emoji icon")
    source: str = Field(..., description="Authoritative source")
    tags: List[str] = Field(default_factory=list, description="Search tags")


class TriviaConfigResponse(BaseModel):
    """Response for trivia configuration."""

    total_questions: int
    questions: List[TriviaQuestion]


class BreathingConfigResponse(BaseModel):
    """Response for breathing exercise configuration."""

    total_exercises: int
    exercises: List[BreathingExercise]
    default_exercise: str


class TipsConfigResponse(BaseModel):
    """Response for daily tips configuration."""

    tips_by_category: dict[str, List[HealthTip]]
    total_tips: int
    categories: List[str]


# ============================================================================
# Helper Functions
# ============================================================================


def load_json_config(file_path: Path) -> dict[str, Any]:
    """Load and parse JSON config file."""
    if not file_path.exists():
        raise FileNotFoundError(f"Config file not found: {file_path}")

    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


# ============================================================================
# Endpoints
# ============================================================================


@router.get(
    "/widget-config/trivia",
    response_model=TriviaConfigResponse,
    tags=["Widget Configs"],
    summary="Get trivia questions configuration",
    description="""
    Returns configurable trivia questions from config/tv_widgets/trivia.json.

    Doctors can edit this file to add custom trivia questions without code changes.

    **Card**: FI-TV-REFAC-002
    """,
)
async def get_trivia_config(
    difficulty: Literal["easy", "medium", "hard"] | None = None,
    limit: int | None = None,
) -> TriviaConfigResponse:
    """
    Get trivia questions from config file.

    Optional filtering by difficulty and limit.
    """
    try:
        config = load_json_config(TRIVIA_CONFIG)
        questions = [TriviaQuestion(**q) for q in config["questions"]]

        # Filter by difficulty
        if difficulty:
            questions = [q for q in questions if q.difficulty == difficulty]

        # Shuffle for variety
        random.shuffle(questions)

        # Limit results
        if limit and limit > 0:
            questions = questions[:limit]

        logger.info(
            "Served trivia config",
            total=len(questions),
            difficulty=difficulty,
            limit=limit,
        )

        return TriviaConfigResponse(
            total_questions=len(questions),
            questions=questions,
        )

    except FileNotFoundError as e:
        logger.error("Trivia config file not found", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trivia config not found: {e!s}",
        )
    except Exception as e:
        logger.error("Failed to load trivia config", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load trivia config: {e!s}",
        )


@router.get(
    "/widget-config/breathing",
    response_model=BreathingConfigResponse,
    tags=["Widget Configs"],
    summary="Get breathing exercises configuration",
)
async def get_breathing_config(
    exercise_id: str | None = None,
) -> BreathingConfigResponse:
    """
    Get breathing exercises from config file.

    If exercise_id is provided, returns only that exercise.
    Otherwise returns all exercises.
    """
    try:
        config = load_json_config(BREATHING_CONFIG)
        exercises = [BreathingExercise(**ex) for ex in config["exercises"]]

        # Filter by exercise_id
        if exercise_id:
            exercises = [ex for ex in exercises if ex.id == exercise_id]
            if not exercises:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Exercise {exercise_id} not found",
                )

        logger.info(
            "Served breathing config",
            total=len(exercises),
            exercise_id=exercise_id,
        )

        return BreathingConfigResponse(
            total_exercises=len(exercises),
            exercises=exercises,
            default_exercise=config.get("default_exercise", exercises[0].id if exercises else ""),
        )

    except HTTPException:
        raise
    except FileNotFoundError as e:
        logger.error("Breathing config file not found", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Breathing config not found: {e!s}",
        )
    except Exception as e:
        logger.error("Failed to load breathing config", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load breathing config: {e!s}",
        )


@router.get(
    "/widget-config/daily-tips",
    response_model=TipsConfigResponse,
    tags=["Widget Configs"],
    summary="Get daily health tips configuration",
)
async def get_daily_tips_config(
    category: Literal["nutrition", "exercise", "mental_health", "prevention"] | None = None,
) -> TipsConfigResponse:
    """
    Get daily health tips from config file.

    If category is provided, returns only tips from that category.
    Otherwise returns all tips organized by category.
    """
    try:
        config = load_json_config(TIPS_CONFIG)
        tips_dict = config["tips"]

        # Parse tips into Pydantic models
        tips_by_category = {}
        for cat, tip_list in tips_dict.items():
            tips_by_category[cat] = [HealthTip(**tip) for tip in tip_list]

        # Filter by category
        if category:
            tips_by_category = {category: tips_by_category.get(category, [])}

        total_tips = sum(len(tips) for tips in tips_by_category.values())
        categories = list(tips_by_category.keys())

        logger.info(
            "Served daily tips config",
            total=total_tips,
            categories=len(categories),
            filter_category=category,
        )

        return TipsConfigResponse(
            tips_by_category=tips_by_category,
            total_tips=total_tips,
            categories=categories,
        )

    except FileNotFoundError as e:
        logger.error("Daily tips config file not found", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Daily tips config not found: {e!s}",
        )
    except Exception as e:
        logger.error("Failed to load daily tips config", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load daily tips config: {e!s}",
        )


@router.get(
    "/widget-config/random-tip",
    tags=["Widget Configs"],
    summary="Get a random daily tip",
)
async def get_random_tip(
    category: Literal["nutrition", "exercise", "mental_health", "prevention"] | None = None,
) -> HealthTip:
    """
    Get a single random health tip.

    Useful for TV display rotation.
    """
    try:
        config = load_json_config(TIPS_CONFIG)
        tips_dict = config["tips"]

        # Select category
        if category:
            if category not in tips_dict:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Category {category} not found",
                )
            tip_list = tips_dict[category]
        else:
            # Random category
            all_tips = []
            for tip_list in tips_dict.values():
                all_tips.extend(tip_list)
            tip_list = all_tips

        if not tip_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No tips found",
            )

        # Random tip
        random_tip_data = random.choice(tip_list)
        tip = HealthTip(**random_tip_data)

        logger.info("Served random tip", tip_id=tip.id, category=category)
        return tip

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get random tip", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get random tip: {e!s}",
        )
