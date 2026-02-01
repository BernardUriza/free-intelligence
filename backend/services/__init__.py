"""Backend Services Layer - Extracted from core/.

Business logic services organized by domain:
- soap: SOAP note generation (13 files)
- kpi: KPIs and metrics aggregation (6 files)
- analysis: Emotional and clinical analysis (2 files)
- checkin: Patient check-in conversations (3 files)
- content: Content management (2 files)
- document: Document handling (2 files)
- evidence: Clinical evidence service (4 files)
- export: Data export utilities (3 files)

Phase 1 extraction complete: 8 services, ~35 files moved from core/services/.

Each service exports its own public API via __init__.py:
    from backend.services.soap import SOAPGenerationService
    from backend.services.kpi import PersonaMetricsService
    from backend.services.checkin import CheckinConversationService
    etc.

See: .claude/rules/architecture/backend-refactor-analysis.md
"""

__all__ = []  # Services export their own public APIs via their __init__.py
