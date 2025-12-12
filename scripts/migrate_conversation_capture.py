#!/usr/bin/env python3
"""
Script para migrar ConversationCapture.tsx a usar hooks especializados.

Realiza búsqueda y reemplazo sistemático de referencias.

Usage:
    python scripts/migrate_conversation_capture.py
"""

import re
from pathlib import Path

# Archivo objetivo
TARGET_FILE = Path("apps/aurity/components/medical/ConversationCapture.tsx")

# Mapeo de reemplazos (orden importa!)
REPLACEMENTS = [
    # Session state
    (r"\bsessionId\b(?!Ref|:)", "session.sessionId"),
    (r"\bsetSessionId\b", "session.setSessionId"),
    (r"\bsessionIdRef\.current\b", "session.sessionIdRef.current"),
    # Pause/Resume
    (r"\bisPaused\b", "session.isPaused"),
    (r"\bsetIsPaused\b", "session.setIsPaused"),
    (r"\bpausedAudioUrl\b", "session.pausedAudioUrl"),
    (r"\bsetPausedAudioUrl\b", "session.setPausedAudioUrl"),
    # Patient info
    (r"\bpatientInfo\b(?!:)", "session.patientInfo"),
    (r"\bsetPatientInfo\b", "session.setPatientInfo"),
    (r"\bshowPatientInfoModal\b", "session.showPatientInfoModal"),
    (r"\bsetShowPatientInfoModal\b", "session.setShowPatientInfoModal"),
    # Diarization
    (r"\bdiarizationJobId\b", "session.diarizationJobId"),
    (r"\bsetDiarizationJobId\b", "session.setDiarizationJobId"),
    (r"\bshowDiarizationModal\b", "session.showDiarizationModal"),
    (r"\bsetShowDiarizationModal\b", "session.setShowDiarizationModal"),
    # Error & state
    (r"\berror\b(?!:)", "session.error"),
    (r"\bsetError\b", "session.setError"),
    (r"\bisFinalized\b", "session.isFinalized"),
    (r"\bsetIsFinalized\b", "session.setIsFinalized"),
    (r"\bisWaitingForChunks\b", "session.isWaitingForChunks"),
    (r"\bsetIsWaitingForChunks\b", "session.setIsWaitingForChunks"),
    (r"\bshouldFinalize\b", "session.shouldFinalize"),
    (r"\bsetShouldFinalize\b", "session.setShouldFinalize"),
    # Checkpoint
    (r"\bcheckpointState\b", "session.checkpointState"),
    (r"\bsetCheckpointState\b", "session.setCheckpointState"),
    (r"\bestimatedSecondsRemaining\b", "session.estimatedSecondsRemaining"),
    (r"\bsetEstimatedSecondsRemaining\b", "session.setEstimatedSecondsRemaining"),
    (r"\bfinalizationStartTimeRef\.current\b", "session.finalizationStartTimeRef.current"),
    # Audio upload refs
    (r"\bchunkNumberRef\.current\b", "audioUpload.chunkNumberRef.current"),
    (r"\baudioChunksRef\.current\b", "audioUpload.audioChunksRef.current"),
    (r"\bfullAudioBlobsRef\.current\b", "audioUpload.fullAudioBlobsRef.current"),
    (r"\binflightRef\.current\b", "audioUpload.inflightRef.current"),
    # Metrics (addLog es el más común)
    (r"\baddLog\b", "metrics.addLog"),
]


def migrate_file():
    """Realiza la migración del archivo."""

    if not TARGET_FILE.exists():
        print(f"❌ Archivo no encontrado: {TARGET_FILE}")
        return False

    # Leer contenido original
    content = TARGET_FILE.read_text()
    original_lines = len(content.splitlines())

    print(f"📄 Migrando {TARGET_FILE}")
    print(f"📏 Líneas originales: {original_lines}")
    print()

    # Aplicar reemplazos
    changes_count = 0
    for pattern, replacement in REPLACEMENTS:
        matches = len(re.findall(pattern, content))
        if matches > 0:
            content = re.sub(pattern, replacement, content)
            changes_count += matches
            print(f"✅ {matches:3d} cambios: {pattern:40s} → {replacement}")

    print()
    print(f"📊 Total de cambios: {changes_count}")

    # Guardar archivo migrado
    TARGET_FILE.write_text(content)
    print(f"💾 Archivo guardado: {TARGET_FILE}")

    return True


if __name__ == "__main__":
    print("=" * 70)
    print("🔧 Migración de ConversationCapture a Hooks Especializados")
    print("=" * 70)
    print()

    success = migrate_file()

    print()
    if success:
        print("✅ Migración completada!")
        print()
        print("Próximos pasos:")
        print("1. Verificar errores de linter")
        print("2. Testing manual del componente")
        print("3. Commit de cambios")
    else:
        print("❌ Migración fallida")
        exit(1)
