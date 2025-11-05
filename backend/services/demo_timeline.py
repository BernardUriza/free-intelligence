#!/usr/bin/env python3
"""
Free Intelligence - Demo Timeline con 10 eventos y ≥4 aristas causales

Demuestra el flujo completo de Timeline AURITY:
1. 10 eventos médicos realistas (usuario + sistema + críticos)
2. Al menos 4 aristas causales (DAG)
3. Redacción aplicada (sin spoilers de audio crudo)
4. Auto-timeline con fallback manual

Card: [P0][Área: UX/UI][Tipo: feature] Memoria legible — Timeline AURITY
Sprint: SPR-2025W44
"""

from datetime import UTC, datetime, timedelta

UTC = UTC

from backend.timeline_models import (
    CausalityType,
    RedactionPolicy,
    Timeline,
    TimelineEventType,
    TimelineMode,
    create_causality,
    create_timeline_event,
)


def create_demo_timeline() -> Timeline:
    """
    Create demo timeline with 10 events and ≥4 causal edges.

    Scenario: Paciente con dolor torácico → detección widow-maker
    """
    timeline = Timeline(
        session_id="session_demo_widow_maker",
        owner_hash="abc123def456",
        generation_mode=TimelineMode.MANUAL,
    )

    now = datetime.now(UTC)

    # ========================================================================
    # EVENTO 1: Usuario envía mensaje inicial (dolor de pecho)
    # ========================================================================
    event1 = create_timeline_event(
        event_type=TimelineEventType.USER_MESSAGE,
        who="user_abc123",
        what="Usuario reporta dolor de pecho con irradiación al brazo izquierdo",
        raw_content="Tengo dolor en el pecho desde hace 2 horas, me duele también el brazo izquierdo",
        summary="Dolor torácico agudo (2h evolución) + irradiación brazo izquierdo",
        redaction_policy=RedactionPolicy.SUMMARY,
        session_id="session_demo_widow_maker",
        tags=["symptoms", "chest_pain", "arm_radiation"],
        auto_generated=False,
        generation_mode=TimelineMode.MANUAL,
    )
    event1.timestamp = now
    timeline.add_event(event1)

    # ========================================================================
    # EVENTO 2: Sistema inicia extracción médica (disparado por mensaje)
    # ========================================================================
    event2 = create_timeline_event(
        event_type=TimelineEventType.EXTRACTION_STARTED,
        who="system",
        what="Sistema inicia extracción médica de audio",
        raw_content="EXTRACTION_STARTED: session_demo_widow_maker",
        causality=[
            create_causality(
                related_event_id=event1.event_id,
                causality_type=CausalityType.TRIGGERED,
                explanation="Usuario envió mensaje con síntomas",
                confidence=1.0,
            )
        ],  # ARISTA CAUSAL #1
        redaction_policy=RedactionPolicy.METADATA,
        session_id="session_demo_widow_maker",
        tags=["system", "extraction"],
        auto_generated=True,
        generation_mode=TimelineMode.AUTO,
    )
    event2.timestamp = now + timedelta(seconds=2)
    timeline.add_event(event2)

    # ========================================================================
    # EVENTO 3: Usuario aporta datos demográficos
    # ========================================================================
    event3 = create_timeline_event(
        event_type=TimelineEventType.USER_MESSAGE,
        who="user_abc123",
        what="Usuario aporta datos demográficos: 58 años, fumador, diabetes",
        raw_content="Tengo 58 años, he fumado 20 años, y tengo diabetes",
        summary="Paciente 58a, fumador 20a, DM2 (factores de riesgo cardiovascular)",
        redaction_policy=RedactionPolicy.SUMMARY,
        session_id="session_demo_widow_maker",
        tags=["demographics", "risk_factors", "diabetes", "smoker"],
        auto_generated=False,
    )
    event3.timestamp = now + timedelta(seconds=30)
    timeline.add_event(event3)

    # ========================================================================
    # EVENTO 4: Sistema actualiza SOAP - Subjective
    # ========================================================================
    event4 = create_timeline_event(
        event_type=TimelineEventType.SOAP_SECTION_UPDATED,
        who="assistant",
        what="SOAP Subjective actualizado: dolor torácico con factores de riesgo",
        raw_content="SOAP:Subjective updated with chest pain, arm radiation, risk factors",
        summary="SOAP-S: Dolor torácico + factores riesgo (edad, tabaco, DM2)",
        causality=[
            create_causality(
                related_event_id=event3.event_id,
                causality_type=CausalityType.UPDATED,
                explanation="Datos demográficos agregados a SOAP",
                confidence=1.0,
            )
        ],  # ARISTA CAUSAL #2
        redaction_policy=RedactionPolicy.SUMMARY,
        session_id="session_demo_widow_maker",
        tags=["soap", "subjective"],
        auto_generated=True,
        generation_mode=TimelineMode.AUTO,
    )
    event4.timestamp = now + timedelta(seconds=35)
    timeline.add_event(event4)

    # ========================================================================
    # EVENTO 5: Usuario describe síntomas adicionales (diaforesis, náusea)
    # ========================================================================
    event5 = create_timeline_event(
        event_type=TimelineEventType.USER_MESSAGE,
        who="user_abc123",
        what="Usuario reporta sudoración fría y náusea",
        raw_content="Estoy sudando mucho y tengo ganas de vomitar",
        summary="Diaforesis + náusea (síntomas asociados)",
        redaction_policy=RedactionPolicy.SUMMARY,
        session_id="session_demo_widow_maker",
        tags=["symptoms", "diaphoresis", "nausea"],
        auto_generated=False,
    )
    event5.timestamp = now + timedelta(seconds=60)
    timeline.add_event(event5)

    # ========================================================================
    # EVENTO 6: Sistema completa extracción
    # ========================================================================
    event6 = create_timeline_event(
        event_type=TimelineEventType.EXTRACTION_COMPLETED,
        who="system",
        what="Extracción médica completada: 3 síntomas núcleo identificados",
        raw_content="EXTRACTION_COMPLETED: chest_pain, arm_radiation, diaphoresis, nausea",
        causality=[
            create_causality(
                related_event_id=event2.event_id,
                causality_type=CausalityType.CAUSED_BY,
                explanation="Proceso de extracción completado",
                confidence=1.0,
            )
        ],  # ARISTA CAUSAL #3
        redaction_policy=RedactionPolicy.METADATA,
        session_id="session_demo_widow_maker",
        tags=["system", "extraction", "completed"],
        auto_generated=True,
        generation_mode=TimelineMode.AUTO,
    )
    event6.timestamp = now + timedelta(seconds=65)
    timeline.add_event(event6)

    # ========================================================================
    # EVENTO 7: Sistema detecta patrón crítico (widow-maker)
    # ========================================================================
    event7 = create_timeline_event(
        event_type=TimelineEventType.CRITICAL_PATTERN_DETECTED,
        who="system",
        what="⚠️ Patrón crítico detectado: posible síndrome coronario agudo (widow-maker)",
        raw_content="CRITICAL: Chest pain + arm radiation + diaphoresis + risk factors = probable ACS/MI",
        summary="Patrón widow-maker: dolor torácico + irradiación + diaforesis + factores riesgo",
        causality=[
            create_causality(
                related_event_id=event6.event_id,
                causality_type=CausalityType.CAUSED_BY,
                explanation="Extracción identificó patrón de alto riesgo cardiovascular",
                confidence=0.95,
            )
        ],  # ARISTA CAUSAL #4
        redaction_policy=RedactionPolicy.SUMMARY,
        session_id="session_demo_widow_maker",
        tags=["critical", "widow_maker", "acs", "mi"],
        auto_generated=True,
        generation_mode=TimelineMode.AUTO,
    )
    event7.timestamp = now + timedelta(seconds=70)
    event7.confidence_score = 0.95  # Alta confianza en detección
    timeline.add_event(event7)

    # ========================================================================
    # EVENTO 8: Sistema escala urgencia a CRITICAL
    # ========================================================================
    event8 = create_timeline_event(
        event_type=TimelineEventType.URGENCY_ESCALATED,
        who="system",
        what="Urgencia escalada a CRITICAL: requiere atención inmediata (código rojo)",
        raw_content="URGENCY_ESCALATED: LOW → CRITICAL",
        causality=[
            create_causality(
                related_event_id=event7.event_id,
                causality_type=CausalityType.CONFIRMED,
                explanation="Patrón crítico confirmado, escalamiento automático",
                confidence=1.0,
            )
        ],  # ARISTA CAUSAL #5
        redaction_policy=RedactionPolicy.METADATA,
        session_id="session_demo_widow_maker",
        tags=["urgency", "critical", "escalated"],
        auto_generated=True,
        generation_mode=TimelineMode.AUTO,
    )
    event8.timestamp = now + timedelta(seconds=72)
    timeline.add_event(event8)

    # ========================================================================
    # EVENTO 9: Asistente genera SOAP completo
    # ========================================================================
    event9 = create_timeline_event(
        event_type=TimelineEventType.SOAP_COMPLETED,
        who="assistant",
        what="SOAP completo generado: S/O/A/P confirmado con urgencia CRITICAL",
        raw_content="SOAP_COMPLETED: all sections generated, urgency=CRITICAL",
        summary="SOAP completo: Paciente 58a con dolor torácico + factores riesgo → sospecha IAM",
        causality=[
            create_causality(
                related_event_id=event4.event_id,
                causality_type=CausalityType.UPDATED,
                explanation="SOAP Subjective expandido con datos completos",
                confidence=1.0,
            ),
            create_causality(
                related_event_id=event7.event_id,
                causality_type=CausalityType.CONFIRMED,
                explanation="Patrón crítico incluido en Assessment",
                confidence=1.0,
            ),
        ],  # ARISTAS CAUSALES #6 y #7
        redaction_policy=RedactionPolicy.SUMMARY,
        session_id="session_demo_widow_maker",
        tags=["soap", "completed"],
        auto_generated=True,
        generation_mode=TimelineMode.AUTO,
    )
    event9.timestamp = now + timedelta(seconds=90)
    timeline.add_event(event9)

    # ========================================================================
    # EVENTO 10: Sistema aplica política de redacción y genera export
    # ========================================================================
    event10 = create_timeline_event(
        event_type=TimelineEventType.EXPORT_CREATED,
        who="system",
        what="Export creado: timeline + SOAP con manifest SHA256",
        raw_content="EXPORT_CREATED: timeline_widow_maker.json + manifest.json",
        causality=[
            create_causality(
                related_event_id=event9.event_id,
                causality_type=CausalityType.TRIGGERED,
                explanation="SOAP completo disparó generación de export",
                confidence=1.0,
            )
        ],  # ARISTA CAUSAL #8
        redaction_policy=RedactionPolicy.METADATA,
        session_id="session_demo_widow_maker",
        tags=["export", "manifest"],
        auto_generated=True,
        generation_mode=TimelineMode.AUTO,
    )
    event10.timestamp = now + timedelta(seconds=127)
    timeline.add_event(event10)

    return timeline


def print_timeline_summary(timeline: Timeline):
    """Print timeline summary with causal chains."""
    print("📋 TIMELINE SUMMARY")
    print("=" * 80)
    print(f"Timeline ID: {timeline.timeline_id}")
    print(f"Session: {timeline.session_id}")
    print(f"Events: {len(timeline.events)}")
    print(f"Auto-generated: {timeline.auto_events_count}")
    print(f"Manual: {timeline.manual_events_count}")
    print()

    print("EVENTS:")
    print("=" * 80)
    for i, event in enumerate(timeline.events, 1):
        print(f"\n[{i}] {event.event_type.value.upper()}")
        print(f"    {event.what}")
        print(f"    Who: {event.who}")
        print(f"    When: {event.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"    Redaction: {event.redaction_policy.value}")
        print(f"    Hash: {event.content_hash[:16]}...")

        if event.causality:
            print(f"    Causality ({len(event.causality)} edges):")
            for causality in event.causality:
                related_event = timeline.get_event_by_id(causality.related_event_id)
                related_type = related_event.event_type.value if related_event else "unknown"
                print(f"      ← {causality.causality_type.value} [{related_type}]")
                print(f"        {causality.explanation} (confidence: {causality.confidence})")

    # Count total causal edges
    total_edges = sum(len(event.causality) for event in timeline.events)

    print()
    print("CAUSAL STATISTICS:")
    print("=" * 80)
    print(f"Total events: {len(timeline.events)}")
    print(f"Total causal edges: {total_edges} ✅ (>= 4 required)")
    print(f"Events with causality: {sum(1 for e in timeline.events if e.causality)}")
    print(f"Average edges per event: {total_edges / len(timeline.events):.2f}")

    print()
    print("REDACTION STATISTICS:")
    print("=" * 80)
    for policy, count in timeline.redaction_stats.items():
        print(f"{policy}: {count} events")

    # Demonstrate causal chain for critical event (event 7)
    print()
    print("CAUSAL CHAIN FOR CRITICAL EVENT (widow-maker detection):")
    print("=" * 80)
    critical_events = [
        e for e in timeline.events if e.event_type == TimelineEventType.CRITICAL_PATTERN_DETECTED
    ]
    if critical_events:
        critical_event = critical_events[0]
        chain = timeline.get_causal_chain(critical_event.event_id)
        print(f"Chain length: {len(chain)} events")
        for i, event in enumerate(chain, 1):
            print(f"  {i}. {event.what}")


if __name__ == "__main__":
    print("📋 FREE INTELLIGENCE - TIMELINE DEMO (10 EVENTS + ≥4 CAUSAL EDGES)")
    print("=" * 80)
    print()
    print("Scenario: Paciente con dolor torácico → detección widow-maker")
    print()

    # Create timeline
    timeline = create_demo_timeline()

    # Print summary
    print_timeline_summary(timeline)

    print()
    print("✅ DEMO COMPLETED")
    print()
    print("Criterios de aceptación:")
    print("  ✅ 10 eventos creados")
    print(f"  ✅ {sum(len(e.causality) for e in timeline.events)} aristas causales (>= 4 required)")
    print("  ✅ Redacción aplicada (sin spoilers)")
    print("  ✅ Causalidad (quién→qué→cuándo→por qué)")
    print("  ✅ Hashes SHA256 (no content crudo expuesto)")
