from __future__ import annotations

"""
Free Intelligence - Exporters

Export interactions to Markdown, JSON, and other formats with mandatory manifests.

FI-EXPORT-FEAT-001, FI-EXPORT-FEAT-002
"""

import json
from datetime import timezone, datetime
from pathlib import Path
from typing import Optional

from backend.corpus_ops import read_interactions
from backend.export_policy import create_export_manifest
from backend.logger import get_logger
from backend.search import search_by_session

logger = get_logger(__name__)


def export_to_markdown(
    corpus_path: str,
    output_path: str,
    session_id: Optional[str] = None,
    limit: Optional[int] = None,
) -> str:
    """
    Export interactions to Markdown format with manifest.

    Args:
        corpus_path: Path to HDF5 corpus
        output_path: Output directory path
        session_id: Optional session ID filter
        limit: Optional limit on number of interactions

    Returns:
        Path to created .md file

    Examples:
        >>> export_to_markdown(
        ...     "storage/corpus.h5",
        ...     "exports/",
        ...     session_id="session_20251028_010000"
        ... )
    """
    logger.info(
        "MARKDOWN_EXPORT_STARTED", corpus_path=corpus_path, session_id=session_id, limit=limit
    )

    try:
        # Get interactions
        if session_id:
            interactions = search_by_session(corpus_path, session_id)
        else:
            interactions = read_interactions(corpus_path, limit=limit if limit else 100)

        if not interactions:
            raise ValueError("No interactions to export")

        # Create output directory
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"export_{timestamp}.md"
        md_path = output_dir / filename

        # Write Markdown
        with open(md_path, "w", encoding="utf-8") as f:
            # Header
            f.write("# Free Intelligence - Interaction Export\n\n")
            f.write(f"**Export Date**: {datetime.now(timezone.utc).isoformat()}Z\n\n")
            if session_id:
                f.write(f"**Session**: {session_id}\n\n")
            f.write(f"**Total Interactions**: {len(interactions)}\n\n")
            f.write("---\n\n")

            # Interactions
            for i, interaction in enumerate(interactions, 1):
                f.write(f"## Interaction {i}\n\n")
                f.write(f"**ID**: `{interaction['interaction_id']}`\n\n")
                f.write(f"**Session**: {interaction['session_id']}\n\n")
                f.write(f"**Timestamp**: {interaction['timestamp']}\n\n")
                f.write(f"**Model**: {interaction['model']}\n\n")
                f.write(f"**Tokens**: {interaction['tokens']}\n\n")
                f.write("### Prompt\n\n")
                f.write(f"{interaction['prompt']}\n\n")
                f.write("### Response\n\n")
                f.write(f"{interaction['response']}\n\n")
                f.write("---\n\n")

        logger.info("MARKDOWN_WRITTEN", path=str(md_path))

        # Create manifest
        manifest = create_export_manifest(
            export_filepath=Path(md_path),
            exported_by="system",  # Could be user_id in future
            data_source="/interactions/" if not session_id else f"/interactions/{session_id}",
            format="markdown",
            purpose="backup",
            includes_pii=True,
        )

        # Save manifest
        manifest_path = output_dir / f"{filename}.manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest.__dict__, f, indent=2)

        logger.info("EXPORT_MANIFEST_CREATED", manifest_path=str(manifest_path))

        logger.info(
            "MARKDOWN_EXPORT_COMPLETED", md_path=str(md_path), manifest_path=str(manifest_path)
        )

        return str(md_path)

    except Exception as e:
        logger.error("MARKDOWN_EXPORT_FAILED", error=str(e))
        raise


def export_to_json(
    corpus_path: str,
    output_path: str,
    session_id: Optional[str] = None,
    limit: Optional[int] = None,
) -> str:
    """
    Export interactions to JSON format with manifest.

    Args:
        corpus_path: Path to HDF5 corpus
        output_path: Output directory path
        session_id: Optional session ID filter
        limit: Optional limit on number of interactions

    Returns:
        Path to created .json file

    Examples:
        >>> export_to_json(
        ...     "storage/corpus.h5",
        ...     "exports/",
        ...     session_id="session_20251028_010000"
        ... )
    """
    logger.info("JSON_EXPORT_STARTED", corpus_path=corpus_path, session_id=session_id, limit=limit)

    try:
        # Get interactions
        if session_id:
            interactions = search_by_session(corpus_path, session_id)
        else:
            interactions = read_interactions(corpus_path, limit=limit if limit else 100)

        if not interactions:
            raise ValueError("No interactions to export")

        # Create output directory
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"export_{timestamp}.json"
        json_path = output_dir / filename

        # Prepare data
        export_data = {
            "export_timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "session_id": session_id,
            "total_interactions": len(interactions),
            "interactions": interactions,
        }

        # Write JSON
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        logger.info("JSON_WRITTEN", path=str(json_path))

        # Create manifest
        manifest = create_export_manifest(
            export_filepath=Path(json_path),
            exported_by="system",
            data_source="/interactions/" if not session_id else f"/interactions/{session_id}",
            format="json",
            purpose="backup",
            includes_pii=True,
        )

        # Save manifest
        manifest_path = output_dir / f"{filename}.manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest.__dict__, f, indent=2)

        logger.info("EXPORT_MANIFEST_CREATED", manifest_path=str(manifest_path))

        logger.info(
            "JSON_EXPORT_COMPLETED", json_path=str(json_path), manifest_path=str(manifest_path)
        )

        return str(json_path)

    except Exception as e:
        logger.error("JSON_EXPORT_FAILED", error=str(e))
        raise


if __name__ == "__main__":
    """Demo script"""
    from backend.config_loader import load_config

    config = load_config()
    corpus_path = config["storage"]["corpus_path"]

    print("📦 Free Intelligence - Exporter Demo")
    print("=" * 60)

    # Create exports directory
    exports_dir = Path("exports")
    exports_dir.mkdir(exist_ok=True)

    print("\n1️⃣  Exporting last 5 interactions to Markdown...")
    try:
        md_path = export_to_markdown(corpus_path, str(exports_dir), limit=5)
        print(f"   ✅ Markdown exported: {md_path}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n2️⃣  Exporting last 5 interactions to JSON...")
    try:
        json_path = export_to_json(corpus_path, str(exports_dir), limit=5)
        print(f"   ✅ JSON exported: {json_path}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n" + "=" * 60)
    print("Demo complete!")
