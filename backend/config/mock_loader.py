"""Mock Data Loader - Carga datos desde archivos JSON para desarrollo."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIG_DIR = Path(__file__).parent


class MockDataLoader:
    """Carga datos mock desde archivos JSON."""

    @staticmethod
    def load_json(filename: str) -> dict[str, Any]:
        """Carga un archivo JSON."""
        filepath = CONFIG_DIR / filename
        try:
            with open(filepath, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError as e:
            msg = f"Mock data file not found: {filepath}"
            raise FileNotFoundError(msg) from e
        except json.JSONDecodeError as e:
            msg = f"Invalid JSON in {filepath}"
            raise ValueError(msg) from e

    @staticmethod
    def get_coaches() -> list[dict[str, Any]]:
        """Obtiene lista de coaches."""
        data = MockDataLoader.load_json("mock_coaches.json")
        return data.get("coaches", [])

    @staticmethod
    def get_coach(coach_id: str) -> dict[str, Any] | None:
        """Obtiene un coach por ID."""
        coaches = MockDataLoader.get_coaches()
        return next((c for c in coaches if c["id"] == coach_id), None)

    @staticmethod
    def get_athletes() -> list[dict[str, Any]]:
        """Obtiene lista de athletes."""
        data = MockDataLoader.load_json("mock_athletes.json")
        return data.get("athletes", [])

    @staticmethod
    def get_athlete(athlete_id: str) -> dict[str, Any] | None:
        """Obtiene un athlete por ID."""
        athletes = MockDataLoader.get_athletes()
        return next((a for a in athletes if a["id"] == athlete_id), None)

    @staticmethod
    def get_athletes_by_coach(coach_id: str) -> list[dict[str, Any]]:
        """Obtiene athletes asignados a un coach."""
        athletes = MockDataLoader.get_athletes()
        return [a for a in athletes if a["coachId"] == coach_id]

    @staticmethod
    def get_sessions() -> list[dict[str, Any]]:
        """Obtiene lista de sessions."""
        data = MockDataLoader.load_json("mock_sessions.json")
        return data.get("sessions", [])

    @staticmethod
    def get_session(session_id: str) -> dict[str, Any] | None:
        """Obtiene una session por ID."""
        sessions = MockDataLoader.get_sessions()
        return next((s for s in sessions if s["id"] == session_id), None)

    @staticmethod
    def get_sessions_by_coach(coach_id: str) -> list[dict[str, Any]]:
        """Obtiene sessions de un coach."""
        sessions = MockDataLoader.get_sessions()
        return [s for s in sessions if s["coachId"] == coach_id]

    @staticmethod
    def get_sessions_by_athlete(athlete_id: str) -> list[dict[str, Any]]:
        """Obtiene sessions asignadas a un athlete."""
        sessions = MockDataLoader.get_sessions()
        return [s for s in sessions if s.get("athleteId") == athlete_id]

    @staticmethod
    def get_recent_sessions(coach_id: str, limit: int = 5) -> list[dict[str, Any]]:
        """Obtiene sesiones recientes de un coach."""
        sessions = MockDataLoader.get_sessions_by_coach(coach_id)
        # Sort by createdAt descending
        sorted_sessions = sorted(sessions, key=lambda x: x.get("createdAt", ""), reverse=True)
        return sorted_sessions[:limit]
