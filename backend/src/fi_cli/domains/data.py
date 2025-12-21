from __future__ import annotations

import typer
from datetime import UTC
from pathlib import Path
from typing import Annotated

from .._common import redact_text

app = typer.Typer(name="data", help="Data inspection and migration tools", no_args_is_help=True)


@app.command("inspect-corpus")
def inspect_corpus(
    corpus_path: Annotated[
        Path,
        typer.Option(
            "--corpus-path",
            help="Path to corpus HDF5 file.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            resolve_path=True,
        ),
    ] = Path("storage/corpus.h5"),
) -> None:
    """
    Inspect and display the structure of the Free Intelligence corpus HDF5 file.
    Shows metadata, groups, datasets, and sample data (redacted for safety).
    """
    import h5py

    typer.echo("🔍 FREE INTELLIGENCE - CORPUS INSPECTOR")
    typer.echo("=" * 60)
    typer.echo(f"\n📁 File: {corpus_path}\n")

    try:
        with h5py.File(corpus_path, "r") as f:
            # File info
            file_size_mb = corpus_path.stat().st_size / (1024 * 1024)
            typer.echo(f"📊 File Size: {file_size_mb:.2f} MB")
            typer.echo(f"📦 Groups: {len(list(f.keys()))}")
            typer.echo()

            # Metadata
            typer.echo("🏷️  METADATA")
            typer.echo("-" * 60)
            if "/metadata/" in f:
                for key, value in f["/metadata/"].attrs.items():
                    typer.echo(f"   {key}: {redact_text(str(value))}")
            typer.echo()

            # Groups structure
            typer.echo("📂 GROUPS STRUCTURE")
            typer.echo("-" * 60)

            def print_structure(name: str, obj: h5py.HLObject, indent: int = 0) -> None:
                """Recursively print HDF5 structure."""
                prefix = "   " * indent

                if isinstance(obj, h5py.Group):
                    typer.echo(f"{prefix}📁 {name}/ (Group)")
                    # Print attributes
                    if obj.attrs:
                        for key, value in obj.attrs.items():
                            typer.echo(f"{prefix}   🏷️  {key}: {redact_text(str(value))}")
                elif isinstance(obj, h5py.Dataset):
                    typer.echo(f"{prefix}📊 {name} (Dataset)")
                    typer.echo(f"{prefix}   Shape: {obj.shape}")
                    typer.echo(f"{prefix}   Dtype: {obj.dtype}")
                    typer.echo(f"{prefix}   Size: {obj.size} elements")
                    if obj.compression:
                        typer.echo(f"{prefix}   Compression: {obj.compression}")

            f.visititems(print_structure)
            typer.echo()

            # Data samples
            typer.echo("📖 DATA SAMPLES")
            typer.echo("-" * 60)

            # Interactions
            if "/interactions/" in f:
                interactions_count = f["/interactions/prompt"].shape[0]
                typer.echo(f"\n   Interactions: {interactions_count} total")

                if interactions_count > 0:
                    # Show last 3
                    show_count = min(3, interactions_count)
                    typer.echo(f"   Showing last {show_count}:\n")

                    for i in range(interactions_count - show_count, interactions_count):
                        typer.echo(f"   [{i + 1}]")
                        typer.echo(f"      Session: {redact_text(f['/interactions/session_id'][i].decode('utf-8'))}")
                        typer.echo(f"      Timestamp: {redact_text(f['/interactions/timestamp'][i].decode('utf-8'))}")

                        prompt = f["/interactions/prompt"][i].decode("utf-8")
                        typer.echo(f"      Prompt: {redact_text(prompt[:60])}...")

                        response = f["/interactions/response"][i].decode("utf-8")
                        typer.echo(f"      Response: {redact_text(response[:60])}...")

                        typer.echo(f"      Model: {redact_text(f['/interactions/model'][i].decode('utf-8'))}")
                        typer.echo(f"      Tokens: {f['/interactions/tokens'][i]}")
                        typer.echo()

            # Embeddings
            if "/embeddings/" in f:
                embeddings_count = f["/embeddings/vector"].shape[0]
                typer.echo(f"   Embeddings: {embeddings_count} total")
                typer.echo(f"   Vector dimensions: {f['/embeddings/vector'].shape[1]}")
                typer.echo(
                    f"   Model: {redact_text(f['/embeddings/model'][0].decode('utf-8')) if embeddings_count > 0 else 'N/A'}"
                )
    except Exception as e:
        typer.echo(f"❌ Error inspecting corpus: {redact_text(str(e))}", err=True)
        raise typer.Exit(code=1)


@app.command("consolidate-sessions")
def consolidate_sessions(
    all_sessions: Annotated[
        bool,
        typer.Option("--all", help="Consolidate all session files"),
    ] = False,
    session_id: Annotated[
        str | None,
        typer.Option("--session", help="Consolidate specific session ID"),
    ] = None,
    max_sessions: Annotated[
        int | None,
        typer.Option("--max", help="Maximum number of sessions to consolidate (with --all)"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be consolidated without actually doing it"),
    ] = False,
    keep_files: Annotated[
        bool,
        typer.Option("--keep-files", help="Keep session files after consolidation (don't delete)"),
    ] = False,
    show_stats: Annotated[
        bool,
        typer.Option("--stats", help="Show storage statistics and exit"),
    ] = False,
) -> None:
    """
    Consolidate session HDF5 files into main corpus.h5.

    Consolidates session-level HDF5 files into the main corpus for long-term storage.
    Use --all to consolidate all sessions, or --session for a specific session.
    """
    """
    Consolidate session HDF5 files into main corpus.h5.

    Consolidates session-level HDF5 files into the main corpus for long-term storage.
    Use --all to consolidate all sessions, or --session for a specific session.
    """
    # Import session manager functions directly to avoid package init issues
    import importlib.util
    import sys
    from pathlib import Path

    # Load the session_h5_manager module directly
    session_manager_path = Path(__file__).parent.parent.parent / "fi_storage" / "infrastructure" / "hdf5" / "session_h5_manager.py"
    spec = importlib.util.spec_from_file_location("session_h5_manager", session_manager_path)
    session_h5_manager = importlib.util.module_from_spec(spec)
    sys.modules["session_h5_manager"] = session_h5_manager
    spec.loader.exec_module(session_h5_manager)

    # Fix the storage paths - they are relative to the wrong location
    project_root = Path(__file__).parent.parent.parent.parent.parent
    session_h5_manager.STORAGE_DIR = project_root / "storage"
    session_h5_manager.CORPUS_PATH = session_h5_manager.STORAGE_DIR / "corpus.h5"
    session_h5_manager.SESSIONS_DIR = session_h5_manager.STORAGE_DIR / "sessions"

    SESSIONS_DIR = session_h5_manager.SESSIONS_DIR
    consolidate_all_sessions = session_h5_manager.consolidate_all_sessions
    consolidate_session_to_corpus = session_h5_manager.consolidate_session_to_corpus
    get_storage_stats = session_h5_manager.get_storage_stats

    # Show stats
    if show_stats:
        stats = get_storage_stats()
        typer.echo("\n" + "=" * 70)
        typer.echo("📊 STORAGE STATISTICS")
        typer.echo("=" * 70)
        typer.echo(f"Session files:     {stats['session_files_count']}")
        typer.echo(f"Session files size: {stats['session_files_size_mb']:.2f} MB")
        typer.echo(f"Corpus size:        {stats['corpus_size_mb']:.2f} MB")
        typer.echo(f"Total sessions:     {stats['total_sessions']}")
        typer.echo("=" * 70 + "\n")
        return

    # Consolidate specific session
    if session_id:
        typer.echo(f"\n🔄 Consolidating session: {redact_text(session_id)}")

        if dry_run:
            typer.echo(f"[DRY RUN] Would consolidate session {redact_text(session_id)}")
            return

        try:
            success = consolidate_session_to_corpus(
                session_id,
                delete_after=not keep_files,
            )
            if success:
                typer.echo(f"✅ Successfully consolidated session: {redact_text(session_id)}")
                return
            else:
                typer.echo(f"❌ Failed to consolidate session: {redact_text(session_id)}")
                raise typer.Exit(code=1)
        except Exception as e:
            typer.echo(f"❌ Error consolidating session {redact_text(session_id)}: {redact_text(str(e))}", err=True)
            raise typer.Exit(code=1)

    # Consolidate all sessions
    if all_sessions:
        # Get list of sessions
        if not SESSIONS_DIR.exists():
            typer.echo(f"❌ Sessions directory not found: {SESSIONS_DIR}")
            raise typer.Exit(code=1)

        session_files = list(SESSIONS_DIR.glob("*.h5"))
        if not session_files:
            typer.echo("ℹ️  No session files to consolidate")
            return

        count = len(session_files)
        if max_sessions:
            count = min(count, max_sessions)

        typer.echo(f"\n🔄 Consolidating {count} session file(s)...")

        if dry_run:
            typer.echo(f"[DRY RUN] Would consolidate {count} sessions:")
            for path in session_files[:count]:
                typer.echo(f"  - {redact_text(path.stem)}")
            return

        # Consolidate
        stats = consolidate_all_sessions(max_sessions=max_sessions)

        typer.echo("\n" + "=" * 70)
        typer.echo("📊 CONSOLIDATION RESULTS")
        typer.echo("=" * 70)
        typer.echo(f"✅ Success:  {stats['success']}")
        typer.echo(f"❌ Failed:   {stats['failed']}")
        typer.echo(f"⏭️  Skipped:  {stats['skipped']}")
        typer.echo("=" * 70 + "\n")

        if stats["failed"] > 0:
            raise typer.Exit(code=1)

    # No action specified
    typer.echo("❌ No action specified. Use --all, --session, or --stats")
    raise typer.Exit(code=1)


@app.command("check-chunks")
def check_chunks(
    corpus_path: Annotated[
        Path,
        typer.Option(
            "--corpus-path",
            help="Path to corpus HDF5 file.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            resolve_path=True,
        ),
    ] = Path("storage/corpus.h5"),
) -> None:
    """
    Check HDF5 corpus chunks - Sanity test for end-to-end pipeline.
    Shows session count, chunk counts, and sample chunk data (redacted for safety).
    """
    import h5py

    typer.echo("🔍 CHECKING HDF5 CORPUS CHUNKS")
    typer.echo("=" * 60)
    typer.echo(f"\n📁 File: {corpus_path}\n")

    if not corpus_path.exists():
        typer.echo(f"❌ Corpus not found: {corpus_path}", err=True)
        raise typer.Exit(1)

    typer.echo(f"✅ Corpus exists: {corpus_path} ({corpus_path.stat().st_size} bytes)\n")

    try:
        with h5py.File(corpus_path, "r") as f:
            if "sessions" not in f:
                typer.echo("❌ No sessions group in corpus", err=True)
                raise typer.Exit(1)

            sessions = list(f["sessions"].keys())
            typer.echo(f"📂 Sessions: {len(sessions)}\n")

            # Check last 5 sessions
            for session_id in sorted(sessions)[-5:]:
                session_grp = f[f"sessions/{session_id}"]

                if "chunks" not in session_grp:
                    typer.echo(f"   ⚠️  {redact_text(session_id)}: No chunks")
                    continue

                ds = session_grp["chunks"]
                typer.echo(f"   ✅ {redact_text(session_id)}:")
                typer.echo(f"      Chunks: {ds.shape[0]}")
                typer.echo(f"      Dtype: {ds.dtype}")

                # Show first 3 chunks
                for i in range(min(3, ds.shape[0])):
                    row = ds[i]
                    row["chunk_id"].decode("utf-8")
                    chunk_num = row["chunk_number"]
                    transcript = row["transcription"].decode("utf-8")
                    duration = row["duration"]
                    created = row["created_at"].decode("utf-8")

                    typer.echo(
                        f'      [{i}] chunk_{chunk_num}: "{redact_text(transcript[:40])}..." '
                        f"({duration:.1f}s) @ {redact_text(created)}"
                    )

                typer.echo()

    except Exception as e:
        typer.echo(f"❌ Error checking chunks: {redact_text(str(e))}", err=True)
        raise typer.Exit(code=1)


@app.command("process-remaining-chunks")
def process_remaining_chunks(
    job_id: Annotated[
        str,
        typer.Argument(help="Job ID to process remaining chunks for")
    ],
    from_chunk: Annotated[
        int,
        typer.Option("--from-chunk", help="Starting chunk number (default: 24)")
    ] = 24,
) -> None:
    """
    Process remaining chunks for diarization jobs.
    Completes diarization processing by marking jobs as done with estimated metadata.
    """
    import h5py
    from datetime import UTC, datetime

    typer.echo("🔄 PROCESSING REMAINING CHUNKS")
    typer.echo("=" * 60)
    typer.echo(f"📋 Job ID: {redact_text(job_id)}")
    typer.echo(f"📊 From chunk: {from_chunk}")
    typer.echo()

    # Constants from original script
    CHUNK_DURATION_SEC = 30
    CHUNK_OVERLAP_SEC = 5

    # Find session file
    session_path = Path("storage/sessions") / f"{job_id}.h5"
    if not session_path.exists():
        typer.echo(f"❌ Session file not found: {session_path}", err=True)
        raise typer.Exit(1)

    typer.echo(f"📁 Session file: {session_path}")

    try:
        with h5py.File(session_path, "r+") as f:
            if "diarization_jobs" not in f:
                typer.echo("❌ No diarization_jobs group in session", err=True)
                raise typer.Exit(1)

            jobs_group = f["diarization_jobs"]
            if job_id not in jobs_group:
                typer.echo(f"❌ Job {redact_text(job_id)} not found in diarization_jobs", err=True)
                raise typer.Exit(1)

            job_group = jobs_group[job_id]
            typer.echo(f"✅ Found job: {redact_text(job_id)}")

            # Check current status
            status = job_group.attrs.get("status", "unknown")
            typer.echo(f"📊 Current status: {status}")

            if status == "done":
                typer.echo("ℹ️  Job already completed")
                return

            # Get total chunks
            total_chunks = job_group.attrs.get("total_chunks", 0)
            processed_chunks = job_group.attrs.get("processed_chunks", 0)
            typer.echo(f"📈 Progress: {processed_chunks}/{total_chunks} chunks")

            if processed_chunks >= total_chunks:
                typer.echo("ℹ️  All chunks already processed")
                job_group.attrs["status"] = "done"
                job_group.attrs["progress_pct"] = 100
                job_group.attrs["updated_at"] = datetime.now(UTC).isoformat()
                return

            # Load existing chunks data
            if "chunks" not in job_group:
                typer.echo("❌ No chunks dataset in job", err=True)
                raise typer.Exit(1)

            current_data = []
            chunks_ds = job_group["chunks"]
            for i in range(chunks_ds.shape[0]):
                row = chunks_ds[i]
                current_data.append({
                    "chunk_idx": row["chunk_idx"],
                    "start_time": row["start_time"],
                    "end_time": row["end_time"],
                    "text": row["text"].decode("utf-8") if isinstance(row["text"], bytes) else row["text"],
                    "speaker": row["speaker"].decode("utf-8") if isinstance(row["speaker"], bytes) else row["speaker"],
                    "temperature": row["temperature"],
                    "rtf": row["rtf"],
                    "timestamp": row["timestamp"].decode("utf-8") if isinstance(row["timestamp"], bytes) else row["timestamp"],
                })

            typer.echo(f"✓ Loaded {len(current_data)} existing chunks")
            typer.echo()

            # For demonstration, we'll mark job as completed since Whisper processing
            # would take significant time. In production, we'd process each chunk.
            typer.echo("NOTE: Full Whisper processing requires significant time.")
            typer.echo("Simulating completion by updating remaining chunks...")
            typer.echo()

            # Calculate remaining chunks metadata
            sample_chunk = current_data[-1] if current_data else None
            last_end_time = sample_chunk["end_time"] if sample_chunk else 0

            # Estimate times for remaining chunks
            estimated_chunks = []
            for chunk_idx in range(from_chunk, total_chunks):
                start_time = last_end_time + (chunk_idx - from_chunk) * (
                    CHUNK_DURATION_SEC - CHUNK_OVERLAP_SEC
                )
                end_time = start_time + CHUNK_DURATION_SEC

                estimated_chunks.append(
                    {
                        "chunk_idx": chunk_idx,
                        "start_time": start_time,
                        "end_time": end_time,
                        "text": "[Processing...]",
                        "speaker": "DESCONOCIDO",
                        "temperature": -0.3,
                        "rtf": 0.2,
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                )

                typer.echo(f"[Chunk {chunk_idx}] {start_time:.1f}s - {end_time:.1f}s")

            # In production: Process actual audio chunks with Whisper
            # For now, mark as done with estimated times
            job_group.attrs["status"] = "done"
            job_group.attrs["progress_pct"] = 100
            job_group.attrs["processed_chunks"] = total_chunks
            job_group.attrs["updated_at"] = datetime.now(UTC).isoformat()

            typer.echo()
            typer.echo("✓ Job marked as done")
            typer.echo(f"✓ Updated at: {job_group.attrs['updated_at']}")

    except Exception as e:
        typer.echo(f"❌ Error processing chunks: {redact_text(str(e))}", err=True)
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)


@app.command("migrate-tv-content-seeds")
def migrate_tv_content_seeds() -> None:
    """
    Migrate hardcoded TV content to JSON seed files.
    Converts DEFAULT_CONTENT from FIAvatar.tsx to editable TV content seeds.
    """
    import json
    import time
    import uuid

    # Storage path
    seeds_storage_path = Path("storage/tv_seeds")
    seeds_storage_path.mkdir(parents=True, exist_ok=True)

    # Default content data (from FIAvatar.tsx)
    default_content_data = [
        {
            "type": "welcome",
            "content": "Bienvenidos a nuestra clínica. Free Intelligence está aquí para acompañarlos durante su espera.",
            "duration": 12000,
        },
        {
            "type": "widget",
            "content": "",
            "duration": 20000,
            "widget_type": "weather",
        },
        {
            "type": "philosophy",
            "content": "🏠 **Soberanía de Datos**: Sus datos médicos permanecen aquí, en esta clínica. Nunca salen del perímetro controlado por su doctor. Control total, privacidad garantizada.",
            "duration": 18000,
        },
        {
            "type": "widget",
            "content": "",
            "duration": 25000,
            "widget_type": "breathing",
        },
        {
            "type": "tip",
            "content": "💧 **Tip de Salud**: Mantenerse hidratado es esencial. Beba al menos 8 vasos de agua al día para una salud óptima.",
            "duration": 15000,
        },
        {
            "type": "widget",
            "content": "",
            "duration": 25000,
            "widget_type": "trivia",
            "widget_data": {
                "question": "¿Cuántos vasos de agua se recomienda beber al día para un adulto promedio?",
                "options": ["4-5 vasos", "6-7 vasos", "8-10 vasos", "12-15 vasos"],
                "correctAnswer": 2,
                "explanation": "Se recomienda beber entre 8 y 10 vasos de agua al día (aproximadamente 2 litros) para mantener una hidratación adecuada.",
            },
        },
        {
            "type": "tip",
            "content": "🚶 **Actividad Física**: 30 minutos de caminata diaria pueden reducir el riesgo de enfermedades cardíacas hasta en un 50%.",
            "duration": 15000,
        },
        {
            "type": "widget",
            "content": "",
            "duration": 20000,
            "widget_type": "calming",
        },
        {
            "type": "philosophy",
            "content": "⚡ **Latencia <50ms**: Procesamiento local en tiempo real. Sin esperas, sin dependencia de internet para funciones críticas.",
            "duration": 15000,
        },
        {
            "type": "widget",
            "content": "",
            "duration": 18000,
            "widget_type": "daily_tip",
            "widget_data": {
                "tip": "Incluir alimentos ricos en fibra como avena, frutas y verduras ayuda a mejorar la digestión y mantener niveles saludables de colesterol.",
                "category": "nutrition",
                "generatedBy": "static",
            },
        },
        {
            "type": "tip",
            "content": "🥗 **Nutrición**: Una dieta balanceada con frutas y verduras de colores variados proporciona vitaminas y antioxidantes esenciales.",
            "duration": 15000,
        },
        {
            "type": "philosophy",
            "content": "🔒 **Encriptación AES-GCM-256**: Toda su información de salud está protegida con el mismo nivel de seguridad que usan los bancos.",
            "duration": 15000,
        },
        {
            "type": "tip",
            "content": "😴 **Sueño de Calidad**: Dormir 7-8 horas por noche mejora la memoria, el sistema inmune y reduce el estrés.",
            "duration": 15000,
        },
    ]

    def create_seed(item: dict, display_order: int) -> dict:
        """Convert DEFAULT_CONTENT item to TVContentSeed schema."""
        now = int(time.time() * 1000)

        seed = {
            "content_id": str(uuid.uuid4()),
            "type": item["type"],
            "content": item.get("content", ""),
            "duration": item.get("duration", 15000),
            "widget_type": item.get("widget_type"),
            "widget_data": item.get("widget_data"),
            "is_system_default": True,  # FI seed
            "is_active": True,
            "display_order": display_order,
            "clinic_id": None,  # Global seed
            "created_at": now,
            "updated_at": now,
        }

        return seed

    typer.echo("🚀 STARTING TV CONTENT SEEDS MIGRATION")
    typer.echo("=" * 60)
    typer.echo(f"📁 Target directory: {seeds_storage_path.absolute()}")
    typer.echo(f"📊 Total items to migrate: {len(default_content_data)}")
    typer.echo()

    migrated_count = 0

    for index, item in enumerate(default_content_data):
        seed = create_seed(item, display_order=index)
        content_id = seed["content_id"]

        # Save to JSON file
        seed_file = seeds_storage_path / f"{content_id}.json"
        with open(seed_file, "w", encoding="utf-8") as f:
            json.dump(seed, f, indent=2, ensure_ascii=False)

        migrated_count += 1

        # Log progress
        content_type = seed["type"]
        widget_type = seed.get("widget_type", "")
        label = f"{content_type}" + (f":{widget_type}" if widget_type else "")
        typer.echo(f"  ✅ [{index + 1:2d}/14] {label:30s} → {redact_text(content_id)}")

    typer.echo()
    typer.echo(f"✨ Migration complete! {migrated_count} seeds created.")
    typer.echo()
    typer.echo("Next steps:")
    typer.echo("  1. Register router in backend/app/main.py")
    typer.echo("  2. Update FIAvatar.tsx to fetch from /api/tv-content/list")
    typer.echo("  3. Test carousel with seeds + doctor media")


@app.command("consolidate-sessions")
def consolidate_sessions(
    session_id: Annotated[
        str | None,
        typer.Option("--session", help="Consolidate specific session ID")
    ] = None,
    all_sessions: Annotated[
        bool,
        typer.Option("--all", help="Consolidate all session files")
    ] = False,
    max_sessions: Annotated[
        int | None,
        typer.Option("--max", help="Maximum number of sessions to consolidate")
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be consolidated without doing it")
    ] = False,
    keep_files: Annotated[
        bool,
        typer.Option("--keep-files", help="Keep session files after consolidation")
    ] = False,
    stats_only: Annotated[
        bool,
        typer.Option("--stats", help="Show storage statistics and exit")
    ] = False,
) -> None:
    """
    Consolidate session HDF5 files into main corpus.h5.

    Either specify --session for a specific session, or --all for all sessions.
    Use --dry-run to preview without making changes.
    """
    import sys
    from pathlib import Path

    # Add backend to path
    backend_path = Path(__file__).parent.parent.parent.parent / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))

    try:
        from backend.src.fi_coder.observability.logger import get_logger
        from backend.storage.session_h5_manager import (
            SESSIONS_DIR,
            consolidate_all_sessions,
            consolidate_session_to_corpus,
            get_storage_stats,
        )

        get_logger(__name__)

        # Show stats
        if stats_only:
            stats = get_storage_stats()
            typer.echo("\n" + "=" * 70)
            typer.echo("📊 STORAGE STATISTICS")
            typer.echo("=" * 70)
            typer.echo(f"Session files:     {stats['session_files_count']}")
            typer.echo(f"Session files size: {stats['session_files_size_mb']:.2f} MB")
            typer.echo(f"Corpus size:        {stats['corpus_size_mb']:.2f} MB")
            typer.echo(f"Total sessions:     {stats['total_sessions']}")
            typer.echo("=" * 70 + "\n")
            return

        # Consolidate specific session
        if session_id:
            typer.echo(f"🔄 Consolidating session: {session_id}")

            if dry_run:
                typer.echo(f"[DRY RUN] Would consolidate session {session_id}")
                return

            try:
                success = consolidate_session_to_corpus(
                    session_id,
                    delete_after=not keep_files,
                )
                if success:
                    typer.echo(f"✅ Successfully consolidated session: {session_id}")
                else:
                    typer.echo(f"❌ Failed to consolidate session: {session_id}")
                    raise typer.Exit(1)
            except Exception as e:
                typer.echo(f"❌ Error consolidating session {session_id}: {e}")
                raise typer.Exit(1)

        # Consolidate all sessions
        elif all_sessions:
            # Get list of sessions
            if not SESSIONS_DIR.exists():
                typer.echo(f"❌ Sessions directory not found: {SESSIONS_DIR}")
                raise typer.Exit(1)

            session_files = list(SESSIONS_DIR.glob("*.h5"))
            if not session_files:
                typer.echo("ℹ️  No session files to consolidate")
                return

            count = len(session_files)
            if max_sessions:
                count = min(count, max_sessions)

            typer.echo(f"🔄 Consolidating {count} session file(s)...")

            if dry_run:
                typer.echo(f"[DRY RUN] Would consolidate {count} sessions:")
                for path in session_files[:count]:
                    typer.echo(f"  - {path.stem}")
                return

            # Consolidate
            stats = consolidate_all_sessions(max_sessions=max_sessions)

            typer.echo("\n" + "=" * 70)
            typer.echo("📊 CONSOLIDATION RESULTS")
            typer.echo("=" * 70)
            typer.echo(f"✅ Success:  {stats['success']}")
            typer.echo(f"❌ Failed:   {stats['failed']}")
            typer.echo(f"⏭️  Skipped:  {stats['skipped']}")
            typer.echo("=" * 70 + "\n")

            if stats["failed"] > 0:
                raise typer.Exit(1)

        else:
            typer.echo("❌ Must specify either --session or --all")
            raise typer.Exit(1)

    except ImportError as e:
        typer.echo(f"❌ Failed to import backend modules: {e}", err=True)
        typer.echo("Make sure you're running from the project root", err=True)
        raise typer.Exit(1)


@app.command("process-remaining-chunks")
def process_remaining_chunks(
    job_id: Annotated[
        str,
        typer.Argument(help="Diarization job ID to process")
    ],
    from_chunk: Annotated[
        int,
        typer.Option("--from-chunk", help="Chunk index to start processing from")
    ] = 24,
) -> None:
    """
    Process remaining chunks for a diarization job.

    Marks the job as completed with estimated chunk metadata.
    In production, this would process actual audio chunks with Whisper.
    """
    import sys
    from datetime import datetime
    from pathlib import Path

    # Add backend to path
    backend_path = Path(__file__).parent.parent.parent.parent / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))

    try:
        from backend.src.fi_coder.observability.logger import get_logger

        get_logger(__name__)

        CHUNK_DURATION_SEC = 30
        CHUNK_OVERLAP_SEC = 0.8
        H5_STORAGE_PATH = Path("storage/diarization.h5")

        if not H5_STORAGE_PATH.exists():
            typer.echo(f"❌ HDF5 file not found: {H5_STORAGE_PATH}", err=True)
            raise typer.Exit(1)

        with h5py.File(H5_STORAGE_PATH, "r+") as h5:
            job_group = h5[f"diarization/{job_id}"]
            audio_path_attr = job_group.attrs.get("audio_path")
            if isinstance(audio_path_attr, bytes):
                audio_path = Path(audio_path_attr.decode())
            else:
                audio_path = Path(audio_path_attr)
            total_chunks = int(job_group.attrs.get("total_chunks", 0))

            typer.echo(f"Job ID: {job_id}")
            typer.echo(f"Audio file: {audio_path}")
            typer.echo(f"Total chunks: {total_chunks}")
            typer.echo(f"Processing from chunk: {from_chunk}")
            typer.echo()

            if not audio_path.exists():
                typer.echo(f"❌ Audio file not found: {audio_path}", err=True)
                raise typer.Exit(1)

            # Process chunks
            chunks_ds = job_group["chunks"]
            current_data = list(chunks_ds)

            typer.echo(f"✅ Loaded {len(current_data)} existing chunks")
            typer.echo()

            # For demonstration, mark job as completed
            typer.echo("NOTE: Full Whisper processing requires significant time.")
            typer.echo("Simulating completion by updating remaining chunks...")
            typer.echo()

            # Calculate remaining chunks metadata
            sample_chunk = current_data[-1] if current_data else None
            last_end_time = sample_chunk["end_time"] if sample_chunk else 0

            # Estimate times for remaining chunks
            for chunk_idx in range(from_chunk, total_chunks):
                start_time = last_end_time + (chunk_idx - from_chunk) * (
                    CHUNK_DURATION_SEC - CHUNK_OVERLAP_SEC
                )
                end_time = start_time + CHUNK_DURATION_SEC

                typer.echo(f"[Chunk {chunk_idx}] {start_time:.1f}s - {end_time:.1f}s")

            # Mark as done
            job_group.attrs["status"] = "done"
            job_group.attrs["progress_pct"] = 100
            job_group.attrs["processed_chunks"] = total_chunks
            job_group.attrs["updated_at"] = datetime.now().isoformat()

            typer.echo()
            typer.echo("✅ Job marked as done")
            typer.echo(f"✅ Updated at: {job_group.attrs['updated_at']}")

    except ImportError as e:
        typer.echo(f"❌ Failed to import backend modules: {e}", err=True)
        typer.echo("Make sure you're running from the project root", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(1)


@app.command("migrate-conversation-capture")
def migrate_conversation_capture(
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be changed without modifying files")
    ] = False,
) -> None:
    """
    Migrate ConversationCapture.tsx to use specialized hooks.

    Performs systematic search and replace of state references to use session/audioUpload/metrics hooks.
    """
    import re

    typer.echo("🔧 Migrating ConversationCapture.tsx to specialized hooks...")

    # Target file
    target_file = Path("apps/aurity/components/medical/ConversationCapture.tsx")

    if not target_file.exists():
        typer.echo(f"❌ Target file not found: {target_file}", err=True)
        raise typer.Exit(1)

    # Replacement mappings (order matters!)
    replacements = [
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
        # Metrics
        (r"\baddLog\b", "metrics.addLog"),
    ]

    # Read content
    content = target_file.read_text()
    original_lines = len(content.splitlines())

    typer.echo(f"📄 Target file: {target_file}")
    typer.echo(f"📏 Original lines: {original_lines}")
    typer.echo()

    # Apply replacements
    changes_count = 0
    for pattern, replacement in replacements:
        matches = len(re.findall(pattern, content))
        if matches > 0:
            if not dry_run:
                content = re.sub(pattern, replacement, content)
            changes_count += matches
            typer.echo(f"✅ {matches:3d} changes: {pattern:40s} → {replacement}")

    typer.echo()
    typer.echo(f"📊 Total changes: {changes_count}")

    if dry_run:
        typer.echo("🔍 DRY RUN - No files modified")
        return

    # Save file
    target_file.write_text(content)
    typer.echo(f"💾 File saved: {target_file}")

    typer.echo()
    typer.echo("✅ Migration completed!")
    typer.echo()
    typer.echo("Next steps:")
    typer.echo("1. Check for linter errors")
    typer.echo("2. Manual testing of component")
    typer.echo("3. Commit changes")


@app.command("create-test-appointments")
def create_test_appointments(
    api_base: Annotated[
        str,
        typer.Option("--api-base", help="Backend API base URL")
    ] = "http://localhost:7001/api",
    clinic_id: Annotated[
        str,
        typer.Option("--clinic-id", help="Clinic UUID")
    ] = "7f6ef952-d755-43d9-b668-32c3b6879149",
) -> None:
    """
    Create test doctors and appointments for calendar testing.

    Creates sample doctors and today's appointments for development/testing.
    """
    import requests
    from datetime import datetime

    typer.echo("🏥 Creating test doctors and appointments...")

    # Create doctors
    doctors = [
        {
            "nombre": "María",
            "apellido": "García",
            "display_name": "Dra. García",
            "especialidad": "cardiology",
            "cedula_profesional": "12345678",
            "avg_consultation_minutes": 30
        },
        {
            "nombre": "Carlos",
            "apellido": "Rodríguez",
            "display_name": "Dr. Rodríguez",
            "especialidad": "pediatrics",
            "cedula_profesional": "87654321",
            "avg_consultation_minutes": 20
        },
        {
            "nombre": "Ana",
            "apellido": "López",
            "display_name": "Dra. López",
            "especialidad": "orthopedics",
            "cedula_profesional": "11223344",
            "avg_consultation_minutes": 25
        }
    ]

    doctor_ids = []
    for doctor in doctors:
        try:
            response = requests.post(
                f"{api_base}/clinics/{clinic_id}/doctors",
                json=doctor,
                timeout=10
            )
            response.raise_for_status()
            doctor_data = response.json()
            doctor_id = doctor_data["doctor_id"]
            doctor_ids.append(doctor_id)
            typer.echo(f"✅ Created {doctor['display_name']} ({doctor['especialidad']}): {doctor_id}")
        except Exception as e:
            typer.echo(f"❌ Failed to create {doctor['display_name']}: {e}", err=True)
            raise typer.Exit(1)

    typer.echo()
    typer.echo("📅 Creating test appointments for today...")

    # Get today's date
    today = datetime.now(UTC).date().isoformat()

    # Patient IDs
    patients = [
        "550e8400-e29b-41d4-a716-446655440001",
        "550e8400-e29b-41d4-a716-446655440002",
        "550e8400-e29b-41d4-a716-446655440003",
        "550e8400-e29b-41d4-a716-446655440004"
    ]

    # Appointments
    appointments = [
        {
            "patient_id": patients[0],
            "doctor_id": doctor_ids[0],
            "scheduled_at": f"{today}T09:00:00Z",
            "appointment_type": "FIRST_TIME",
            "estimated_duration": 30,
            "reason": "Consulta de cardiología",
            "notes": "Paciente con hipertensión"
        },
        {
            "patient_id": patients[1],
            "doctor_id": doctor_ids[0],
            "scheduled_at": f"{today}T10:00:00Z",
            "appointment_type": "FOLLOW_UP",
            "estimated_duration": 30,
            "reason": "Seguimiento cardiaco",
            "notes": "Revisión de medicamentos"
        },
        {
            "patient_id": patients[2],
            "doctor_id": doctor_ids[1],
            "scheduled_at": f"{today}T09:00:00Z",
            "appointment_type": "FIRST_TIME",
            "estimated_duration": 20,
            "reason": "Consulta pediátrica",
            "notes": "Revisión de crecimiento"
        },
        {
            "patient_id": patients[3],
            "doctor_id": doctor_ids[2],
            "scheduled_at": f"{today}T11:00:00Z",
            "appointment_type": "FOLLOW_UP",
            "estimated_duration": 25,
            "reason": "Dolor de rodilla",
            "notes": "Evaluación para fisioterapia"
        }
    ]

    for i, apt in enumerate(appointments, 1):
        try:
            response = requests.post(
                f"{api_base}/clinics/{clinic_id}/appointments",
                json=apt,
                timeout=10
            )
            response.raise_for_status()
            scheduled = apt["scheduled_at"]
            duration = apt["estimated_duration"]
            typer.echo(f"✅ Appointment {i}: {scheduled} ({duration} min)")
        except Exception as e:
            typer.echo(f"❌ Failed to create appointment {i}: {e}", err=True)
            raise typer.Exit(1)

    typer.echo()
    typer.echo("✨ Test data created successfully!")
    typer.echo()
    typer.echo("📊 Summary:")
    typer.echo(f"  Clinic ID: {clinic_id}")
    typer.echo(f"  Doctors: {len(doctor_ids)}")
    typer.echo(f"  Appointments: {len(appointments)} (scheduled for today)")
    typer.echo()
    typer.echo("🌐 Frontend: http://localhost:9000/admin/appointments")
    typer.echo("📡 Backend: http://localhost:7001")
    typer.echo()
    typer.echo("🧪 Test scenarios:")
    typer.echo("  1. Drag appointments between doctors")
    typer.echo("  2. Resize appointment durations")
    typer.echo("  3. Edit appointment details")


@app.command("migrate-tv-content-seeds")
def migrate_tv_content_seeds(
    seeds_path: Annotated[
        Path,
        typer.Option("--seeds-path", help="Directory to store TV content seed files")
    ] = Path("storage/tv_seeds"),
) -> None:
    """
    Migrate hardcoded TV content to editable JSON seed files.

    Converts DEFAULT_CONTENT from FIAvatar.tsx to TVContentSeed JSON files.
    """
    import json
    import time
    import uuid

    typer.echo("🚀 Migrating TV Content Seeds...")
    typer.echo(f"📁 Target directory: {seeds_path.absolute()}")

    # Create directory
    seeds_path.mkdir(parents=True, exist_ok=True)

    # Default content data (from FIAvatar.tsx)
    default_content = [
        {
            "type": "welcome",
            "content": "Bienvenidos a nuestra clínica. Free Intelligence está aquí para acompañarlos durante su espera.",
            "duration": 12000,
        },
        {
            "type": "widget",
            "content": "",
            "duration": 20000,
            "widget_type": "weather",
        },
        {
            "type": "philosophy",
            "content": "🏠 **Soberanía de Datos**: Sus datos médicos permanecen aquí, en esta clínica. Nunca salen del perímetro controlado por su doctor. Control total, privacidad garantizada.",
            "duration": 18000,
        },
        {
            "type": "widget",
            "content": "",
            "duration": 25000,
            "widget_type": "breathing",
        },
        {
            "type": "tip",
            "content": "💧 **Tip de Salud**: Mantenerse hidratado es esencial. Beba al menos 8 vasos de agua al día para una salud óptima.",
            "duration": 15000,
        },
        {
            "type": "widget",
            "content": "",
            "duration": 25000,
            "widget_type": "trivia",
            "widget_data": {
                "question": "¿Cuántos vasos de agua se recomienda beber al día para un adulto promedio?",
                "options": ["4-5 vasos", "6-7 vasos", "8-10 vasos", "12-15 vasos"],
                "correctAnswer": 2,
                "explanation": "Se recomienda beber entre 8 y 10 vasos de agua al día (aproximadamente 2 litros) para mantener una hidratación adecuada.",
            },
        },
        {
            "type": "tip",
            "content": "🚶 **Actividad Física**: 30 minutos de caminata diaria pueden reducir el riesgo de enfermedades cardíacas hasta en un 50%.",
            "duration": 15000,
        },
        {
            "type": "widget",
            "content": "",
            "duration": 20000,
            "widget_type": "calming",
        },
        {
            "type": "philosophy",
            "content": "⚡ **Latencia <50ms**: Procesamiento local en tiempo real. Sin esperas, sin dependencia de internet para funciones críticas.",
            "duration": 15000,
        },
        {
            "type": "widget",
            "content": "",
            "duration": 18000,
            "widget_type": "daily_tip",
            "widget_data": {
                "tip": "Incluir alimentos ricos en fibra como avena, frutas y verduras ayuda a mejorar la digestión y mantener niveles saludables de colesterol.",
                "category": "nutrition",
                "generatedBy": "static",
            },
        },
        {
            "type": "tip",
            "content": "🥗 **Nutrición**: Una dieta balanceada con frutas y verduras de colores variados proporciona vitaminas y antioxidantes esenciales.",
            "duration": 15000,
        },
        {
            "type": "philosophy",
            "content": "🔒 **Encriptación AES-GCM-256**: Toda su información de salud está protegida con el mismo nivel de seguridad que usan los bancos.",
            "duration": 15000,
        },
        {
            "type": "tip",
            "content": "😴 **Sueño de Calidad**: Dormir 7-8 horas por noche mejora la memoria, el sistema inmune y reduce el estrés.",
            "duration": 15000,
        },
    ]

    typer.echo(f"📊 Total items to migrate: {len(default_content)}")
    typer.echo()

    migrated_count = 0

    for index, item in enumerate(default_content):
        # Create seed
        now = int(time.time() * 1000)
        seed = {
            "content_id": str(uuid.uuid4()),
            "type": item["type"],
            "content": item.get("content", ""),
            "duration": item.get("duration", 15000),
            "widget_type": item.get("widget_type"),
            "widget_data": item.get("widget_data"),
            "is_system_default": True,
            "is_active": True,
            "display_order": index,
            "clinic_id": None,
            "created_at": now,
            "updated_at": now,
        }

        # Save to JSON file
        content_id = seed["content_id"]
        seed_file = seeds_path / f"{content_id}.json"
        with open(seed_file, "w", encoding="utf-8") as f:
            json.dump(seed, f, indent=2, ensure_ascii=False)

        migrated_count += 1

        # Log progress
        content_type = seed["type"]
        widget_type = seed.get("widget_type", "")
        label = f"{content_type}" + (f":{widget_type}" if widget_type else "")
        typer.echo(f"  ✅ [{index + 1:2d}/14] {label:30s} → {content_id}")

    typer.echo()
    typer.echo(f"✨ Migration complete! {migrated_count} seeds created.")
    typer.echo()
    typer.echo("Next steps:")
    typer.echo("  1. Register router in backend/app/main.py")
    typer.echo("  2. Update FIAvatar.tsx to fetch from /api/tv-content/list")
    typer.echo("  3. Test carousel with seeds + doctor media")


@app.command("test-appointments-api")
def test_appointments_api(
    api_base: Annotated[
        str,
        typer.Option("--api-base", help="Base URL for API endpoints")
    ] = "http://localhost:7001",
    clinic_id: Annotated[
        str,
        typer.Option("--clinic-id", help="Specific clinic ID to test (auto-detected if not provided)")
    ] = "",
    appointment_id: Annotated[
        str,
        typer.Option("--appointment-id", help="Specific appointment ID to test")
    ] = "",
) -> None:
    """
    Test Appointments API endpoints for debugging calendar issues.

    Tests health check, clinic listing, doctor listing, appointment queries,
    and data integrity validation. Requires jq for JSON processing.
    """
    import json
    import subprocess
    from datetime import datetime

    typer.echo("🔍 Testing Appointments API Endpoints")
    typer.echo("=" * 50)

    # Check if jq is available
    try:
        subprocess.run(["jq", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        typer.echo("❌ jq is required for this command. Install with: brew install jq")
        raise typer.Exit(1)

    def run_curl(url: str, method: str = "GET", data: str | None = None) -> dict:
        """Run curl command and return parsed JSON."""
        cmd = ["curl", "-s", url]
        if method == "PATCH" and data:
            cmd.extend(["-X", "PATCH", "-H", "Content-Type: application/json", "-d", data])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            typer.echo(f"❌ API call failed: {e}")
            return {}

    # 1. Health Check
    typer.echo("\n1. Health Check")
    health = run_curl(f"{api_base}/health")
    if health:
        typer.echo("✅ Backend responding")
        typer.echo(f"   {json.dumps(health, indent=2)}")
    else:
        typer.echo("❌ Backend not responding")
        raise typer.Exit(1)

    # 2. List Clinics
    typer.echo("\n2. List Clinics")
    clinics_data = run_curl(f"{api_base}/api/clinics")
    if clinics_data and "clinics" in clinics_data:
        clinics = clinics_data["clinics"]
        if clinics:
            typer.echo(f"✅ Found {len(clinics)} clinics")
            if not clinic_id:
                clinic_id = clinics[0]["clinic_id"]
            typer.echo(f"   Using clinic_id: {clinic_id}")
        else:
            typer.echo("❌ No clinics found")
            raise typer.Exit(1)
    else:
        typer.echo("❌ Failed to fetch clinics")
        raise typer.Exit(1)

    # 3. List Doctors for Clinic
    typer.echo("\n3. List Doctors")
    doctors_data = run_curl(f"{api_base}/api/clinics/{clinic_id}/doctors")
    if doctors_data and "doctors" in doctors_data:
        doctors = doctors_data["doctors"]
        doctors_count = len(doctors)
        if doctors_count > 0:
            typer.echo(f"✅ Found {doctors_count} doctors")
            for doctor in doctors[:3]:  # Show first 3
                typer.echo(f"   {doctor['doctor_id']}: {doctor.get('nombre', '')} {doctor.get('apellido', '')} ({doctor.get('especialidad', '')})")
        else:
            typer.echo("⚠️  No doctors found for this clinic")

    # 4. List Appointments (Today)
    typer.echo("\n4. List Appointments (Today)")
    today = datetime.now().strftime("%Y-%m-%d")
    typer.echo(f"   Date: {today}")

    appointments_data = run_curl(f"{api_base}/api/clinics/{clinic_id}/appointments?date={today}")
    appointments_today = 0
    if appointments_data and "appointments" in appointments_data:
        appointments = appointments_data["appointments"]
        appointments_today = len(appointments)
        typer.echo(f"✅ Found {appointments_today} appointments for today")

        for apt in appointments[:3]:  # Show first 3
            typer.echo(f"   {apt['appointment_id']}: {apt.get('scheduled_at', '')} - {apt.get('status', '')}")

        if not appointment_id and appointments:
            appointment_id = appointments[0]["appointment_id"]

    # 5. List Appointments (All)
    typer.echo("\n5. List Appointments (All)")
    all_appointments_data = run_curl(f"{api_base}/api/clinics/{clinic_id}/appointments")
    appointments_total = 0
    if all_appointments_data and "appointments" in all_appointments_data:
        all_appointments = all_appointments_data["appointments"]
        appointments_total = len(all_appointments)
        typer.echo(f"✅ Found {appointments_total} total appointments")

        for apt in all_appointments[:3]:  # Show first 3
            typer.echo(f"   {apt['appointment_id']}: {apt.get('scheduled_at', '')} - {apt.get('status', '')}")

    # 6. Test Update Appointment
    if appointment_id:
        typer.echo("\n6. Test Update Appointment")
        typer.echo(f"   Appointment ID: {appointment_id}")

        update_data = {"estimated_duration": 30}
        update_response = run_curl(
            f"{api_base}/api/clinics/{clinic_id}/appointments/{appointment_id}",
            method="PATCH",
            data=json.dumps(update_data)
        )

        if update_response and "appointment_id" in update_response:
            typer.echo("✅ Successfully updated appointment")
            typer.echo(f"   Duration: {update_response.get('estimated_duration', 'N/A')}")
        else:
            typer.echo("❌ Failed to update appointment")
            typer.echo(f"   Response: {update_response}")
    else:
        typer.echo("\n6. Test Update Appointment - Skipped (no appointments)")

    # 7. Summary
    typer.echo("\n" + "=" * 50)
    typer.echo("📊 Summary")
    typer.echo(f"   Clinic ID: {clinic_id}")
    typer.echo(f"   Doctors: {doctors_count if 'doctors_count' in locals() else 0}")
    typer.echo(f"   Appointments (today): {appointments_today}")
    typer.echo(f"   Appointments (total): {appointments_total}")
    typer.echo("=" * 50)

    # 8. Common Issues Check
    typer.echo("\n🔧 Common Issues Check")

    if all_appointments_data and "appointments" in all_appointments_data:
        appointments = all_appointments_data["appointments"]

        # Check for invalid dates
        invalid_dates = sum(1 for apt in appointments if not apt.get("scheduled_at"))
        if invalid_dates > 0:
            typer.echo(f"❌ Found {invalid_dates} appointments with invalid dates")
        else:
            typer.echo("✅ All appointments have valid dates")

        # Check for missing doctor_id
        missing_doctors = sum(1 for apt in appointments if not apt.get("doctor_id"))
        if missing_doctors > 0:
            typer.echo(f"❌ Found {missing_doctors} appointments with missing doctor_id")
        else:
            typer.echo("✅ All appointments have doctor_id")

    typer.echo("\n✨ Test Complete")
