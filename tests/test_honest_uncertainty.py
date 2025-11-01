"""
Tests para Honest Uncertainty Messaging

Cobertura:
- No false confidence terms in event names
- Event names reflect operations, not conclusions
- Qualifiers present in validation events
- CLI output admits method and limitations

Autor: Bernard Uriza Orozco
Fecha: 2025-10-26
Task: FI-UI-FIX-001
"""

import sys
import unittest
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from event_validator import CANONICAL_EVENTS


class TestHonestUncertainty(unittest.TestCase):
    """Tests para validar principios de honestidad en eventos."""

    def test_no_passed_in_canonical_events(self):
        """Eventos canónicos no deben usar 'PASSED' (falsa certeza)."""
        passed_events = [e for e in CANONICAL_EVENTS if "PASSED" in e]

        self.assertEqual(
            len(passed_events),
            0,
            f"Found {len(passed_events)} events with 'PASSED': {passed_events}",
        )

    def test_no_verified_in_canonical_events(self):
        """Eventos canónicos no deben usar 'VERIFIED' (falsa prueba)."""
        verified_events = [e for e in CANONICAL_EVENTS if "VERIFIED" in e]

        self.assertEqual(
            len(verified_events),
            0,
            f"Found {len(verified_events)} events with 'VERIFIED': {verified_events}",
        )

    def test_no_success_in_canonical_events(self):
        """Eventos canónicos no deben usar 'SUCCESS' (binario falso)."""
        success_events = [e for e in CANONICAL_EVENTS if "SUCCESS" in e]

        self.assertEqual(
            len(success_events),
            0,
            f"Found {len(success_events)} events with 'SUCCESS': {success_events}",
        )

    def test_validation_events_have_qualifiers(self):
        """Eventos de validación deben tener calificadores honestos."""
        validation_events = [e for e in CANONICAL_EVENTS if "SCAN" in e or "CHECKS" in e]

        # Debe haber eventos de validación
        self.assertGreater(
            len(validation_events), 0, "Should have validation events with honest qualifiers"
        )

        # Todos deben usar COMPLETED o similar
        for event in validation_events:
            self.assertTrue(
                any(q in event for q in ["COMPLETED", "DETECTED"]),
                f"Validation event should use COMPLETED or DETECTED: {event}",
            )

    def test_ownership_events_admit_method(self):
        """Eventos de ownership deben admitir método (hash comparison)."""
        ownership_events = [e for e in CANONICAL_EVENTS if "OWNERSHIP" in e]

        # Debe contener HASH_MATCHED o HASH_MISMATCH
        has_honest_ownership = any("HASH" in e for e in ownership_events)

        self.assertTrue(has_honest_ownership, "Ownership events should admit method (HASH_MATCHED)")

    def test_stats_events_admit_snapshot_nature(self):
        """Eventos de stats deben admitir naturaleza temporal (snapshot)."""
        stats_events = [e for e in CANONICAL_EVENTS if "STATS" in e]

        has_snapshot = any("SNAPSHOT" in e or "COMPUTED" in e for e in stats_events)

        self.assertTrue(
            has_snapshot, "Stats events should admit temporal nature (SNAPSHOT or COMPUTED)"
        )

    def test_no_guaranteed_or_proven(self):
        """No debe haber términos de certeza absoluta."""
        false_certainty_terms = ["GUARANTEED", "PROVEN", "CONFIRMED", "ENSURED"]

        for term in false_certainty_terms:
            events_with_term = [e for e in CANONICAL_EVENTS if term in e]

            self.assertEqual(
                len(events_with_term),
                0,
                f"Should not use absolute certainty term '{term}': {events_with_term}",
            )

    def test_export_events_use_hash_comparison(self):
        """Eventos de export deben admitir método (hash comparison)."""
        export_events = [e for e in CANONICAL_EVENTS if "EXPORT" in e or "MANIFEST" in e]

        has_hash_events = any("HASH" in e for e in export_events)

        self.assertTrue(has_hash_events, "Export events should use HASH_COMPARED or HASH_MATCHED")

    def test_canonical_events_count(self):
        """Debe haber suficientes eventos canónicos."""
        # Actualmente tenemos ~50+ eventos
        self.assertGreater(
            len(CANONICAL_EVENTS),
            40,
            f"Should have at least 40 canonical events, got {len(CANONICAL_EVENTS)}",
        )

    def test_event_names_are_uppercase_snake_case(self):
        """Todos los eventos deben estar en UPPER_SNAKE_CASE."""
        for event in CANONICAL_EVENTS:
            # Debe ser todo mayúsculas
            self.assertEqual(event, event.upper(), f"Event should be uppercase: {event}")

            # Debe tener solo alfanuméricos y underscores
            self.assertTrue(
                all(c.isalnum() or c == "_" for c in event),
                f"Event should only have alphanumeric and underscores: {event}",
            )

            # No debe empezar o terminar con underscore
            self.assertFalse(
                event.startswith("_") or event.endswith("_"),
                f"Event should not start/end with underscore: {event}",
            )

    def test_policy_events_use_scan_not_validation(self):
        """Eventos de políticas deben usar SCAN en lugar de VALIDATION."""
        policy_keywords = ["LLM", "MUTATION", "ROUTER", "APPEND"]

        for keyword in policy_keywords:
            policy_events = [e for e in CANONICAL_EVENTS if keyword in e]

            if policy_events:
                # Si tiene eventos de policy, no debe usar VALIDATION_PASSED
                validation_passed = [e for e in policy_events if "VALIDATION_PASSED" in e]

                self.assertEqual(
                    len(validation_passed),
                    0,
                    f"{keyword} policy events should not use VALIDATION_PASSED: {validation_passed}",
                )


class TestHonestMessagingInCode(unittest.TestCase):
    """Tests para validar mensajes honestos en el código."""

    def test_no_false_confidence_in_backend(self):
        """Archivos backend no deben tener términos de falsa certeza en strings."""
        backend_dir = Path(__file__).parent.parent / "backend"
        false_confidence_patterns = [
            '"VALIDATION_PASSED"',
            '"OWNERSHIP_VERIFIED"',
            '"STATS_RETRIEVED"',
            '"EXPORT_VALIDATED"',
        ]

        violations = []

        for py_file in backend_dir.glob("*.py"):
            content = py_file.read_text()

            for pattern in false_confidence_patterns:
                if pattern in content:
                    violations.append(f"{py_file.name}: {pattern}")

        self.assertEqual(
            len(violations),
            0,
            "Found false confidence patterns in backend:\n" + "\n".join(violations),
        )

    def test_honest_terms_present_in_backend(self):
        """Archivos backend deben usar términos honestos."""
        backend_dir = Path(__file__).parent.parent / "backend"
        honest_patterns = [
            "SCAN_COMPLETED",
            "HASH_MATCHED",
            "SNAPSHOT_COMPUTED",
            "CHECKS_COMPLETED",
        ]

        found_honest_terms = set()

        for py_file in backend_dir.glob("*.py"):
            content = py_file.read_text()

            for pattern in honest_patterns:
                if pattern in content:
                    found_honest_terms.add(pattern)

        # Debe encontrar al menos algunos términos honestos
        self.assertGreater(
            len(found_honest_terms),
            0,
            f"Should find at least some honest terms in backend code. Searched for: {honest_patterns}",
        )


if __name__ == "__main__":
    unittest.main()
