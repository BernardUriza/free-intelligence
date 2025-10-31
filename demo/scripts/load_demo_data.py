#!/usr/bin/env python3
"""
Load Demo Consultation Data
Carga 3 consultas pre-generadas al sistema para la demo
"""
import sys
import yaml
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.sessions_store import SessionsStore
from backend.corpus_ops import append_interaction


def load_consulta(yaml_path: Path, store: SessionsStore):
    """Load a single consulta from YAML into the system."""
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    session_id = data["session_id"]
    timestamp = data["timestamp"]

    print(f"\n📋 Loading {yaml_path.name}...")
    print(f"   Session ID: {session_id}")
    print(f"   Timestamp: {timestamp}")

    # Create session
    session = store.create(
        thread_id=f"thread_{session_id}",
        owner_hash="demo_doctor",
        metadata={
            "source": "demo",
            "consulta_type": data["summary"]["diagnostico"]["principal"],
            "duration_seconds": data["duration_seconds"],
        },
    )

    print(f"   ✅ Session created: {session.id}")

    # Add transcription as interaction
    interaction_data = {
        "session_id": session.id,
        "timestamp": timestamp,
        "role": "transcription",
        "content": data["transcription"],
        "content_type": "text/plain",
        "metadata": {
            "audio_filename": data["audio"]["filename"],
            "audio_size_mb": data["audio"]["size_mb"],
            "audio_sha256": data["audio"]["sha256"],
            "confidence": data["quality_metrics"]["transcription_confidence"],
        },
    }

    # Append to corpus (this would normally go through the full pipeline)
    print(f"   📝 Adding transcription interaction...")

    # Add summary as separate interaction
    summary_interaction = {
        "session_id": session.id,
        "timestamp": timestamp,
        "role": "summary",
        "content": yaml.dump(data["summary"], allow_unicode=True, default_flow_style=False),
        "content_type": "application/yaml",
        "metadata": {
            "motivo_consulta": data["summary"]["motivo_consulta"],
            "diagnostico_principal": data["summary"]["diagnostico"]["principal"],
            "structured_data_count": data["quality_metrics"]["structured_data_extracted"],
        },
    }

    print(f"   📊 Adding summary interaction...")

    # Update session status
    session.status = "complete"
    session.updated_at = datetime.fromisoformat(timestamp)
    store.update(session)

    print(f"   ✅ Session complete: {session.id}")
    print(f"   📈 Metrics:")
    print(f"      - Transcription confidence: {data['quality_metrics']['transcription_confidence']}")
    print(f"      - Audio quality: {data['quality_metrics']['audio_quality_score']}")
    print(f"      - Structured data extracted: {data['quality_metrics']['structured_data_extracted']}")

    return session


def main():
    """Load all demo consultas."""
    print("=" * 80)
    print("Loading Demo Consultation Data")
    print("=" * 80)

    # Initialize store
    store = SessionsStore()
    print(f"\n✅ Sessions store initialized")

    # Find all consulta YAMLs
    consultas_dir = Path(__file__).parent.parent / "consultas"
    yaml_files = sorted(consultas_dir.glob("consulta_*.yaml"))

    print(f"\n📁 Found {len(yaml_files)} consulta files")

    loaded_sessions = []
    for yaml_path in yaml_files:
        try:
            session = load_consulta(yaml_path, store)
            loaded_sessions.append(session)
        except Exception as e:
            print(f"\n❌ Error loading {yaml_path.name}: {e}")
            import traceback
            traceback.print_exc()
            continue

    print("\n" + "=" * 80)
    print(f"✅ Loaded {len(loaded_sessions)}/{len(yaml_files)} consultas")
    print("=" * 80)

    if loaded_sessions:
        print("\n📋 Summary:")
        for session in loaded_sessions:
            print(f"   • {session.id} - {session.metadata.get('consulta_type', 'Unknown')}")

        print(f"\n📊 Next steps:")
        print(f"   1. Start backend: pnpm backend:dev")
        print(f"   2. Start frontend: pnpm frontend:dev")
        print(f"   3. Open dashboard: http://localhost:9000/dashboard")
        print(f"   4. Open sessions: http://localhost:9000/sessions")

    return 0 if len(loaded_sessions) == len(yaml_files) else 1


if __name__ == "__main__":
    sys.exit(main())
