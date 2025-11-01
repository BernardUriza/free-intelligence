#!/usr/bin/env python3
from __future__ import annotations

"""
Free Intelligence - Auto-Timeline Generator

Heurística v1 para generar timeline automáticamente desde event store.
Usa Ollama (qwen2.5 / deepseek-r1-distill-7b) para resumir eventos en lenguaje natural.
Sin spoilers de audio crudo - solo hash + summary.

Card: [P0][Área: UX/UI][Tipo: feature] Memoria legible — Timeline AURITY
Sprint: SPR-2025W44
"""

from dataclasses import dataclass
from datetime import timezone, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import yaml

from backend.llm_adapter import LLMAdapter, LLMRequest
from backend.logger import get_logger
from backend.timeline_models import (
    CausalityType,
    RedactionPolicy,
    Timeline,
    TimelineEvent,
    TimelineEventType,
    TimelineMode,
    create_causality,
    create_timeline_event,
)

logger = get_logger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================


def load_timeline_config() -> dict[str, Any]:
    """Load timeline configuration from fi.policy.yaml."""
    config_path = Path("config/fi.policy.yaml")

    if not config_path.exists():
        logger.warning(
            "TIMELINE_CONFIG_NOT_FOUND",
            config_path=str(config_path),
            details={"fallback": "default config"},
        )
        return {
            "auto": {
                "enabled": False,
                "provider": "ollama",
                "model": "qwen2.5:7b-instruct-q4_0",
                "fallback_to_manual": True,
                "timeout_seconds": 8,
                "selected_events": [
                    "HASH_WRITTEN",
                    "POLICY_CHECK",
                    "FIELD_UPDATED",
                    "LLM_SUMMARY",
                    "DECISION_APPLIED",
                    "EXPORT_GENERATED",
                ],
                "grouping": {"window_seconds": 90, "by_session": True, "by_manifest": True},
                "causality": {
                    "same_artifact_weight": 1.0,
                    "temporal_adjacent_seconds": 30,
                    "same_actor_weight": 0.7,
                },
                "redaction": {
                    "max_summary_chars": 180,
                    "max_preview_chars": 60,
                    "hide_preview_if_sensitive": True,
                    "use_active_verbs": True,
                    "strip_pii": True,
                },
            }
        }

    with open(config_path) as f:
        config = yaml.safe_load(f)

    return config.get("timeline", {})


# ============================================================================
# DATA MODELS
# ============================================================================


@dataclass
class EventCandidate:
    """Candidate event for timeline inclusion."""

    event_type: str
    timestamp: datetime
    who: str  # Actor
    raw_content: str  # Original content (will be hashed)
    session_id: Optional[str] = None
    manifest_ref: Optional[str] = None
    artifact_id: Optional[str] = None  # For causality (same artifact)
    sensitive: bool = False  # If true, no content preview
    metadata: dict[str, Any] = None


@dataclass
class CausalityCandidate:
    """Candidate causal relationship between events."""

    source_event_id: str
    target_event_id: str
    causality_type: CausalityType
    confidence: float  # 0.0-1.0
    explanation: str


# ============================================================================
# AUTO-TIMELINE GENERATOR
# ============================================================================


class AutoTimelineGenerator:
    """
    Auto-timeline generator with Ollama.

    Heurística v1:
    1. Select core events (HASH_WRITTEN, POLICY_CHECK, etc.)
    2. Group by session_id + manifest_ref in 90s windows
    3. Detect causality (same artifact, temporal adjacency)
    4. Generate summaries with LLM (≤180 chars, no PII)
    5. Fallback to manual+assist if LLM fails (timeout >8s)
    """

    def __init__(
        self, llm_adapter: Optional[LLMAdapter] = None, config: Optional[dict[str, Any]] = None
    ):
        """
        Initialize auto-timeline generator.

        Args:
            llm_adapter: LLM adapter (Ollama preferred)
            config: Timeline configuration (from fi.policy.yaml)
        """
        self.config = config or load_timeline_config()
        self.llm = llm_adapter
        self.auto_config = self.config.get("auto", {})

        # Feature flag check
        self.enabled = self.auto_config.get("enabled", False)
        self.timeout_seconds = self.auto_config.get("timeout_seconds", 8)

        logger.info(
            "AUTO_TIMELINE_INITIALIZED",
            enabled=self.enabled,
            provider=self.auto_config.get("provider"),
            model=self.auto_config.get("model"),
            timeout=self.timeout_seconds,
        )

    def is_selected_event(self, event_type: str) -> bool:
        """Check if event type is selected for timeline."""
        selected = self.auto_config.get("selected_events", [])
        return event_type in selected

    def group_events_by_window(
        self, candidates: list[EventCandidate]
    ) -> list[list[EventCandidate]]:
        """
        Group events by time window (90s), session_id, and manifest_ref.

        Args:
            candidates: List of event candidates

        Returns:
            List of event groups (windows)
        """
        window_seconds = self.auto_config.get("grouping", {}).get("window_seconds", 90)
        by_session = self.auto_config.get("grouping", {}).get("by_session", True)
        by_manifest = self.auto_config.get("grouping", {}).get("by_manifest", True)

        # Sort by timestamp
        sorted_candidates = sorted(candidates, key=lambda e: e.timestamp)

        groups = []
        current_group = []
        current_window_start = None
        current_session = None
        current_manifest = None

        for candidate in sorted_candidates:
            # Start new group if:
            # 1. First event
            # 2. Outside window (>90s)
            # 3. Different session (if grouping by session)
            # 4. Different manifest (if grouping by manifest)

            start_new_group = False

            if not current_group:
                start_new_group = True
            else:
                time_delta = (candidate.timestamp - current_window_start).total_seconds()  # type: ignore[operator]
                if time_delta > window_seconds:
                    start_new_group = True
                elif by_session and candidate.session_id != current_session:
                    start_new_group = True
                elif by_manifest and candidate.manifest_ref != current_manifest:
                    start_new_group = True

            if start_new_group:
                if current_group:
                    groups.append(current_group)
                current_group = [candidate]
                current_window_start = candidate.timestamp
                current_session = candidate.session_id
                current_manifest = candidate.manifest_ref
            else:
                current_group.append(candidate)

        # Add last group
        if current_group:
            groups.append(current_group)

        logger.info(
            "AUTO_TIMELINE_GROUPED",
            total_events=len(candidates),
            groups=len(groups),
            window_seconds=window_seconds,
            by_session=by_session,
            by_manifest=by_manifest,
        )

        return groups

    def detect_causality(self, events: list[TimelineEvent]) -> list[CausalityCandidate]:
        """
        Detect causal relationships between events.

        Heuristics:
        - same_artifact: Strong edge (weight=1.0)
        - temporal_adjacent (<30s) + same_actor: Soft edge (weight=0.7)

        Args:
            events: List of timeline events

        Returns:
            List of causality candidates
        """
        causality_config = self.auto_config.get("causality", {})
        same_artifact_weight = causality_config.get("same_artifact_weight", 1.0)
        temporal_adjacent_seconds = causality_config.get("temporal_adjacent_seconds", 30)
        same_actor_weight = causality_config.get("same_actor_weight", 0.7)

        candidates = []

        for i, event in enumerate(events):
            for j in range(i + 1, len(events)):
                next_event = events[j]

                # Check same artifact (strong edge)
                event_artifact = event.reference_id  # artifact_id stored in reference_id
                next_artifact = next_event.reference_id

                if event_artifact and next_artifact and event_artifact == next_artifact:
                    candidates.append(
                        CausalityCandidate(
                            source_event_id=event.event_id,
                            target_event_id=next_event.event_id,
                            causality_type=CausalityType.TRIGGERED,
                            confidence=same_artifact_weight,
                            explanation=f"Same artifact modified: {event_artifact[:8]}...",
                        )
                    )
                    continue

                # Check temporal adjacency + same actor (soft edge)
                time_delta = (next_event.timestamp - event.timestamp).total_seconds()

                if time_delta <= temporal_adjacent_seconds and event.who == next_event.who:
                    candidates.append(
                        CausalityCandidate(
                            source_event_id=event.event_id,
                            target_event_id=next_event.event_id,
                            causality_type=CausalityType.CAUSED_BY,
                            confidence=same_actor_weight,
                            explanation=f"Temporal adjacency ({time_delta:.1f}s) + same actor",
                        )
                    )

        logger.info(
            "AUTO_TIMELINE_CAUSALITY_DETECTED",
            total_events=len(events),
            causality_candidates=len(candidates),
        )

        return candidates

    def generate_summary_with_llm(
        self, raw_content: str, event_type: str, sensitive: bool = False
    ) -> tuple[str, bool]:
        """
        Generate summary with LLM (≤180 chars, no PII, active verbs).

        Args:
            raw_content: Original content
            event_type: Event type for context
            sensitive: If true, hide content preview

        Returns:
            (summary, success) - summary string and success flag
        """
        if not self.llm:
            logger.warning(
                "AUTO_TIMELINE_LLM_NOT_AVAILABLE",
                event_type=event_type,
                details={"fallback": "manual mode"},
            )
            return f"Event: {event_type}", False

        redaction_config = self.auto_config.get("redaction", {})
        max_chars = redaction_config.get("max_summary_chars", 180)
        _strip_pii = redaction_config.get("strip_pii", True)
        _use_active_verbs = redaction_config.get("use_active_verbs", True)

        # Build prompt
        prompt = f"""Summarize this event in Spanish using active voice.
Maximum {max_chars} characters. No PII (names, emails, phone numbers).

Event type: {event_type}
Content: {raw_content[:500]}...

Requirements:
- Use active verbs (not passive voice)
- Maximum {max_chars} characters
- No PII or sensitive data
- Clear and concise

Summary:"""

        try:
            request = LLMRequest(
                prompt=prompt,
                max_tokens=100,  # ~50 chars per token
                temperature=0.5,
                timeout_seconds=self.timeout_seconds,
            )

            start_time = datetime.now(timezone.utc)
            response = self.llm.generate(request)
            latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            summary = response.content.strip()

            # Truncate if needed
            if len(summary) > max_chars:
                summary = summary[: max_chars - 3] + "..."

            logger.info(
                "AUTO_TIMELINE_SUMMARY_GENERATED",
                event_type=event_type,
                summary_length=len(summary),
                latency_ms=int(latency_ms),
                tokens=response.tokens_used,
            )

            return summary, True

        except Exception as e:
            logger.error(
                "AUTO_TIMELINE_SUMMARY_FAILED",
                event_type=event_type,
                error=str(e),
                details={"fallback": "manual mode"},
            )
            return f"Event: {event_type}", False

    def generate_timeline(
        self, session_id: str, owner_hash: str, event_candidates: list[EventCandidate]
    ) -> Timeline:
        """
        Generate timeline from event candidates.

        Args:
            session_id: Session ID
            owner_hash: Owner hash (privacy)
            event_candidates: List of event candidates

        Returns:
            Timeline with events and causality
        """
        if not self.enabled:
            logger.warning(
                "AUTO_TIMELINE_DISABLED",
                session_id=session_id,
                details={"enable_in": "config/fi.policy.yaml → timeline.auto.enabled"},
            )
            return Timeline(
                session_id=session_id, owner_hash=owner_hash, generation_mode=TimelineMode.MANUAL
            )

        logger.info(
            "AUTO_TIMELINE_GENERATION_STARTED",
            session_id=session_id,
            candidates=len(event_candidates),
        )

        # 1. Filter selected events
        selected = [c for c in event_candidates if self.is_selected_event(c.event_type)]

        logger.info(
            "AUTO_TIMELINE_EVENTS_SELECTED", total=len(event_candidates), selected=len(selected)
        )

        # 2. Group by windows
        _groups = self.group_events_by_window(selected)

        # 3. Generate timeline events
        timeline = Timeline(
            session_id=session_id, owner_hash=owner_hash, generation_mode=TimelineMode.AUTO
        )

        timeline_events = []

        for candidate in selected:
            # Generate summary with LLM
            summary, _success = self.generate_summary_with_llm(
                raw_content=candidate.raw_content,
                event_type=candidate.event_type,
                sensitive=candidate.sensitive,
            )

            # Map event type (string → TimelineEventType)
            try:
                event_type = TimelineEventType(candidate.event_type.lower())
            except ValueError:
                # Fallback to user_message if unknown
                event_type = TimelineEventType.USER_MESSAGE

            # Determine redaction policy
            redaction_policy = (
                RedactionPolicy.FULL if candidate.sensitive else RedactionPolicy.SUMMARY
            )

            # Create timeline event
            event = create_timeline_event(
                event_type=event_type,
                who=candidate.who,
                what=summary,
                raw_content=candidate.raw_content,
                summary=summary,
                redaction_policy=redaction_policy,
                session_id=session_id,
                tags=[],
                auto_generated=True,
                generation_mode=TimelineMode.AUTO,
            )

            # Store artifact_id in reference_id for causality
            event.reference_id = candidate.artifact_id

            timeline_events.append(event)
            timeline.add_event(event)

        # 4. Detect causality
        causality_candidates = self.detect_causality(timeline_events)

        # 5. Apply causality to events
        for causality in causality_candidates:
            # Find target event
            target_event = timeline.get_event_by_id(causality.target_event_id)
            if target_event:
                target_event.causality.append(
                    create_causality(
                        related_event_id=causality.source_event_id,
                        causality_type=causality.causality_type,
                        explanation=causality.explanation,
                        confidence=causality.confidence,
                    )
                )

        logger.info(
            "AUTO_TIMELINE_GENERATION_COMPLETED",
            session_id=session_id,
            events=len(timeline.events),
            causality_edges=len(causality_candidates),
            auto_events=timeline.auto_events_count,
        )

        return timeline


# ============================================================================
# CLI DEMO
# ============================================================================

if __name__ == "__main__":
    print("📋 FREE INTELLIGENCE - AUTO-TIMELINE GENERATOR DEMO")
    print("=" * 60)
    print()

    # Load config
    config = load_timeline_config()
    print(f"Config loaded: timeline.auto.enabled = {config.get('auto', {}).get('enabled')}")
    print()

    # Create generator (without LLM for demo)
    generator = AutoTimelineGenerator(llm_adapter=None, config=config)

    # Create event candidates
    now = datetime.now(timezone.utc)

    candidates = [
        EventCandidate(
            event_type="HASH_WRITTEN",
            timestamp=now,
            who="user_abc123",
            raw_content="Audio file hash: abc123def456",
            session_id="session_001",
            manifest_ref="manifest_001",
            artifact_id="audio_001",
        ),
        EventCandidate(
            event_type="POLICY_CHECK",
            timestamp=now + timedelta(seconds=5),
            who="system",
            raw_content="Policy check passed: append-only verified",
            session_id="session_001",
            manifest_ref="manifest_001",
            artifact_id="corpus_001",
        ),
        EventCandidate(
            event_type="LLM_SUMMARY",
            timestamp=now + timedelta(seconds=15),
            who="assistant",
            raw_content="Generated SOAP summary: Patient reports chest pain",
            session_id="session_001",
            manifest_ref="manifest_001",
            artifact_id="soap_001",
            sensitive=True,
        ),
        EventCandidate(
            event_type="EXPORT_GENERATED",
            timestamp=now + timedelta(seconds=120),
            who="user_abc123",
            raw_content="Exported timeline to markdown",
            session_id="session_001",
            manifest_ref="manifest_002",
        ),
    ]

    # Generate timeline (without LLM, will use fallback)
    timeline = generator.generate_timeline(
        session_id="session_demo", owner_hash="abc123", event_candidates=candidates
    )

    print(f"Timeline generated: {timeline.timeline_id}")
    print(f"Events: {len(timeline.events)}")
    print(f"Auto-generated: {timeline.auto_events_count}")
    print()

    print("Events:")
    for i, event in enumerate(timeline.events, 1):
        print(f"\n{i}. [{event.event_type.value}] {event.what}")
        print(f"   Who: {event.who}")
        print(f"   When: {event.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Redaction: {event.redaction_policy.value}")

        if event.causality:
            print("   Causality:")
            for causality in event.causality:
                print(
                    f"      → {causality.causality_type.value}: {causality.explanation} (confidence: {causality.confidence})"
                )

    print()
    print("✅ Auto-timeline demo completed")
