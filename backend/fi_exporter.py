#!/usr/bin/env python3
from __future__ import annotations

"""
Free Intelligence - Corpus Exporter

Export corpus data to portable formats (Markdown, HDF5 subsets).
Supports export_session, export_range, export_user with manifest generation.

FI-EXPORT-FEAT-001
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import h5py  # type: ignore

from backend.export_policy import ExportManifest, create_export_manifest
from backend.logger import get_logger

logger = get_logger(__name__)


def export_session_to_markdown(
    corpus_path: str, session_id: str, output_path: str, include_metadata: bool = True
) -> tuple[str, ExportManifest]:
    """
    Export a single session to Markdown format.

    Args:
        corpus_path: Path to HDF5 corpus
        session_id: Session ID to export
        output_path: Output .md file path
        include_metadata: Include frontmatter with session metadata

    Returns:
        Tuple of (output_path, manifest)

    Raises:
        ValueError: If session_id not found
        FileNotFoundError: If corpus doesn't exist

    Event: EXPORT_SESSION_MARKDOWN_STARTED, EXPORT_SESSION_MARKDOWN_COMPLETED

    Examples:
        >>> path, manifest = export_session_to_markdown(
        ...     "storage/corpus.h5",
        ...     "session_20251028_000000",
        ...     "exports/session.md"
        ... )
        >>> print(f"Exported to {path}")
        Exported to exports/session.md
    """
    logger.info("EXPORT_SESSION_MARKDOWN_STARTED", session_id=session_id, corpus_path=corpus_path)

    corpus_path_obj = Path(corpus_path)
    if not corpus_path_obj.exists():
        raise FileNotFoundError(f"Corpus not found: {corpus_path}")

    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    # Read interactions for session
    interactions = []
    with h5py.File(corpus_path, "r") as f:
        if "/interactions" not in f:
            raise ValueError("No /interactions group in corpus")

        group = f["/interactions"]  # type: ignore[index]
        n_interactions = group["session_id"].shape[0]  # type: ignore[index,attr-defined]

        for i in range(n_interactions):
            sess_id = group["session_id"][i].decode("utf-8")  # type: ignore[index,attr-defined]
            if sess_id == session_id:
                interactions.append(
                    {
                        "interaction_id": group["interaction_id"][i].decode("utf-8"),  # type: ignore[index,attr-defined]
                        "timestamp": group["timestamp"][i].decode("utf-8"),  # type: ignore[index,attr-defined]
                        "prompt": group["prompt"][i].decode("utf-8"),  # type: ignore[index,attr-defined]
                        "response": group["response"][i].decode("utf-8"),  # type: ignore[index,attr-defined]
                        "model": group["model"][i].decode("utf-8"),  # type: ignore[index,attr-defined]
                        "tokens": int(group["tokens"][i]),  # type: ignore[index]
                    }
                )

    if not interactions:
        raise ValueError(f"Session not found: {session_id}")

    # Generate Markdown
    markdown_lines = []

    if include_metadata:
        # Frontmatter
        first_interaction = interactions[0]
        last_interaction = interactions[-1]
        start_time = first_interaction['timestamp']  # type: ignore[index]
        end_time = last_interaction['timestamp']  # type: ignore[index]
        model = first_interaction['model']  # type: ignore[index]
        total_tokens = sum(i['tokens'] for i in interactions)  # type: ignore[index]
        markdown_lines.extend(
            [
                "---",
                f"session_id: {session_id}",
                f"start_time: {start_time}",
                f"end_time: {end_time}",
                f"interactions: {len(interactions)}",
                f"model: {model}",
                f"total_tokens: {total_tokens}",
                f"exported_at: {datetime.now().isoformat()}",
                "---",
                "",
            ]
        )

    # Session header
    markdown_lines.append(f"# Session: {session_id}\n")

    # Interactions
    for idx, interaction in enumerate(interactions, 1):
        timestamp = interaction['timestamp']  # type: ignore[index]
        interaction_id = interaction['interaction_id']  # type: ignore[index]
        prompt = interaction["prompt"]  # type: ignore[index]
        response = interaction["response"]  # type: ignore[index]
        tokens = interaction['tokens']  # type: ignore[index]
        markdown_lines.extend(
            [
                f"## Interaction {idx}",
                f"**Time**: {timestamp}  ",
                f"**ID**: `{interaction_id}`\n",
                "### User Prompt\n",
                prompt,
                "\n### Assistant Response\n",
                response,
                f"\n*Tokens: {tokens}*\n",
                "---\n",
            ]
        )

    # Write to file
    content = "\n".join(markdown_lines)
    output_path_obj.write_text(content, encoding="utf-8")

    logger.info(
        "EXPORT_SESSION_MARKDOWN_COMPLETED",
        session_id=session_id,
        output_path=str(output_path_obj),
        interactions_count=len(interactions),
        file_size=len(content),
    )

    # Create export manifest
    total_tokens_manifest = sum(i["tokens"] for i in interactions)  # type: ignore[index]
    manifest = create_export_manifest(
        exported_by="system",
        data_source=f"/interactions (session_id={session_id})",
        export_filepath=output_path_obj,
        format="markdown",
        purpose="backup",
        includes_pii=True,
        metadata={
            "session_id": session_id,
            "interactions_count": len(interactions),
            "total_tokens": total_tokens_manifest,
        },
    )

    return str(output_path_obj), manifest


def export_range_to_hdf5(
    corpus_path: str,
    output_path: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    session_ids: Optional[list[str]] = None,
) -> tuple[str, ExportManifest]:
    """
    Export a range of interactions to HDF5 subset.

    Args:
        corpus_path: Path to source HDF5 corpus
        output_path: Output .h5 file path
        start_date: Start timestamp (ISO 8601, inclusive)
        end_date: End timestamp (ISO 8601, inclusive)
        session_ids: List of session IDs to export (overrides date range)

    Returns:
        Tuple of (output_path, manifest)

    Raises:
        FileNotFoundError: If corpus doesn't exist
        ValueError: If no interactions match criteria

    Event: EXPORT_RANGE_HDF5_STARTED, EXPORT_RANGE_HDF5_COMPLETED

    Examples:
        >>> path, manifest = export_range_to_hdf5(
        ...     "storage/corpus.h5",
        ...     "exports/backup.h5",
        ...     start_date="2025-10-01T00:00:00",
        ...     end_date="2025-10-31T23:59:59"
        ... )
        >>> print(f"Exported {manifest.metadata['interactions_count']} interactions")
    """
    logger.info(
        "EXPORT_RANGE_HDF5_STARTED",
        corpus_path=corpus_path,
        start_date=start_date,
        end_date=end_date,
        session_ids_count=len(session_ids) if session_ids else 0,
    )

    corpus_path_obj = Path(corpus_path)
    if not corpus_path_obj.exists():
        raise FileNotFoundError(f"Corpus not found: {corpus_path}")

    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    # Read and filter interactions
    filtered_indices = []
    with h5py.File(corpus_path, "r") as f_src:
        if "/interactions" not in f_src:
            raise ValueError("No /interactions group in corpus")

        group = f_src["/interactions"]  # type: ignore[index]
        n_interactions = group["session_id"].shape[0]  # type: ignore[index,attr-defined]

        for i in range(n_interactions):
            # Filter by session_ids if provided
            if session_ids:
                sess_id = group["session_id"][i].decode("utf-8")  # type: ignore[index,attr-defined]
                if sess_id not in session_ids:
                    continue
            # Filter by date range if provided
            elif start_date or end_date:
                timestamp = group["timestamp"][i].decode("utf-8")  # type: ignore[index,attr-defined]
                if start_date and timestamp < start_date:
                    continue
                if end_date and timestamp > end_date:
                    continue

            filtered_indices.append(i)

    if not filtered_indices:
        raise ValueError("No interactions match export criteria")

    # Copy subset to new HDF5
    with h5py.File(corpus_path, "r") as f_src, h5py.File(output_path_obj, "w") as f_dst:
        src_group = f_src["/interactions"]  # type: ignore[index]
        dst_group = f_dst.create_group("/interactions")

        # Copy filtered data
        n_filtered = len(filtered_indices)
        for dataset_name in src_group.keys():
            src_dataset = src_group[dataset_name]
            dtype = src_dataset.dtype
            maxshape = src_dataset.maxshape

            # Create new dataset with filtered size
            dst_dataset = dst_group.create_dataset(
                dataset_name,
                shape=(n_filtered,),
                maxshape=(None,) if maxshape[0] is None else (n_filtered,),
                dtype=dtype,
                compression="gzip",
                compression_opts=4,
            )

            # Copy filtered data
            for new_idx, old_idx in enumerate(filtered_indices):
                dst_dataset[new_idx] = src_dataset[old_idx]

        # Copy metadata
        if "/metadata" in f_src:
            src_meta = f_src["/metadata"]  # type: ignore[index]
            dst_meta = f_dst.create_group("/metadata")
            for attr_name, attr_value in src_meta.attrs.items():
                dst_meta.attrs[attr_name] = attr_value
            dst_meta.attrs["exported_at"] = datetime.now().isoformat()  # type: ignore[index]
            dst_meta.attrs["original_corpus"] = str(corpus_path)  # type: ignore[index]
            dst_meta.attrs["filtered_interactions"] = n_filtered  # type: ignore[index]

    logger.info(
        "EXPORT_RANGE_HDF5_COMPLETED",
        output_path=str(output_path_obj),
        interactions_count=n_filtered,
        file_size=output_path_obj.stat().st_size,
    )

    # Create export manifest
    manifest = create_export_manifest(
        exported_by="system",
        data_source=f"/interactions (filtered: {n_filtered} interactions)",
        export_filepath=output_path_obj,
        format="hdf5",
        purpose="backup",
        includes_pii=True,
        metadata={
            "interactions_count": n_filtered,
            "start_date": start_date,
            "end_date": end_date,
            "session_ids": session_ids,
        },
    )

    return str(output_path_obj), manifest


def export_user_to_markdown(
    corpus_path: str, user_identifier: str, output_path: str, grouped_by_session: bool = True
) -> tuple[str, ExportManifest]:
    """
    Export all interactions for a user to Markdown.

    Args:
        corpus_path: Path to HDF5 corpus
        user_identifier: User email/ID to export
        output_path: Output .md file path
        grouped_by_session: Group interactions by session

    Returns:
        Tuple of (output_path, manifest)

    Raises:
        FileNotFoundError: If corpus doesn't exist
        ValueError: If user not found or no interactions

    Event: EXPORT_USER_MARKDOWN_STARTED, EXPORT_USER_MARKDOWN_COMPLETED

    Examples:
        >>> path, manifest = export_user_to_markdown(
        ...     "storage/corpus.h5",
        ...     "bernard.uriza@example.com",
        ...     "exports/user_export.md"
        ... )
    """
    logger.info(
        "EXPORT_USER_MARKDOWN_STARTED", corpus_path=corpus_path, user_identifier=user_identifier
    )

    corpus_path_obj = Path(corpus_path)
    if not corpus_path_obj.exists():
        raise FileNotFoundError(f"Corpus not found: {corpus_path}")

    # Verify corpus ownership (basic check)
    with h5py.File(corpus_path, "r") as f:
        if "/metadata" not in f:
            raise ValueError("No /metadata in corpus")
        # Note: In real implementation, would hash user_identifier and compare
        # with owner_hash. For simplicity, proceeding with user_identifier.

    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    # Read all interactions (assuming single-user corpus for now)
    sessions_dict = {}
    with h5py.File(corpus_path, "r") as f:
        if "/interactions" not in f:
            raise ValueError("No /interactions group in corpus")

        group = f["/interactions"]  # type: ignore[index]
        n_interactions = group["session_id"].shape[0]  # type: ignore[index,attr-defined]

        for i in range(n_interactions):
            session_id = group["session_id"][i].decode("utf-8")  # type: ignore[index,attr-defined]
            if session_id not in sessions_dict:
                sessions_dict[session_id] = []

            sessions_dict[session_id].append(
                {
                    "interaction_id": group["interaction_id"][i].decode("utf-8"),  # type: ignore[index,attr-defined]
                    "timestamp": group["timestamp"][i].decode("utf-8"),  # type: ignore[index,attr-defined]
                    "prompt": group["prompt"][i].decode("utf-8"),  # type: ignore[index,attr-defined]
                    "response": group["response"][i].decode("utf-8"),  # type: ignore[index,attr-defined]
                    "model": group["model"][i].decode("utf-8"),  # type: ignore[index,attr-defined]
                    "tokens": int(group["tokens"][i]),  # type: ignore[index]
                }
            )

    if not sessions_dict:
        raise ValueError(f"No interactions found for user: {user_identifier}")

    # Generate Markdown
    markdown_lines = []

    # Frontmatter
    total_interactions = sum(len(interactions) for interactions in sessions_dict.values())
    total_tokens = sum(
        sum(i["tokens"] for i in interactions) for interactions in sessions_dict.values()  # type: ignore[index]
    )

    markdown_lines.extend(
        [
            "---",
            f"user: {user_identifier}",
            f"sessions: {len(sessions_dict)}",
            f"total_interactions: {total_interactions}",
            f"total_tokens: {total_tokens}",
            f"exported_at: {datetime.now().isoformat()}",
            "---",
            "",
            f"# User Export: {user_identifier}\n",
            f"**Sessions**: {len(sessions_dict)}  ",
            f"**Total Interactions**: {total_interactions}  ",
            f"**Total Tokens**: {total_tokens}\n",
            "---\n",
        ]
    )

    # Sessions
    for session_id, interactions in sorted(sessions_dict.items()):
        session_tokens = sum(i['tokens'] for i in interactions)  # type: ignore[index]
        markdown_lines.append(f"## Session: {session_id}\n")
        markdown_lines.append(f"**Interactions**: {len(interactions)}  ")
        markdown_lines.append(f"**Tokens**: {session_tokens}\n")

        if grouped_by_session:
            for idx, interaction in enumerate(interactions, 1):
                timestamp = interaction['timestamp']  # type: ignore[index]
                prompt = interaction["prompt"]  # type: ignore[index]
                response = interaction["response"]  # type: ignore[index]
                tokens = interaction['tokens']  # type: ignore[index]
                markdown_lines.extend(
                    [
                        f"### {idx}. {timestamp}\n",
                        "**Prompt**:\n",
                        prompt,
                        "\n**Response**:\n",
                        response,
                        f"\n*Tokens: {tokens}*\n",
                    ]
                )
        else:
            # Flat list
            for interaction in interactions:
                timestamp = interaction['timestamp']  # type: ignore[index]
                prompt = interaction['prompt']  # type: ignore[index]
                response = interaction['response']  # type: ignore[index]
                markdown_lines.extend(
                    [
                        f"**{timestamp}**\n",
                        f"*Prompt*: {prompt}\n",
                        f"*Response*: {response}\n",
                        "---\n",
                    ]
                )

    # Write to file
    content = "\n".join(markdown_lines)
    output_path_obj.write_text(content, encoding="utf-8")

    logger.info(
        "EXPORT_USER_MARKDOWN_COMPLETED",
        user_identifier=user_identifier,
        output_path=str(output_path_obj),
        sessions_count=len(sessions_dict),
        interactions_count=total_interactions,
        file_size=len(content),
    )

    # Create export manifest
    manifest = create_export_manifest(
        exported_by=user_identifier,
        data_source=f"/interactions (user={user_identifier})",
        export_filepath=output_path_obj,
        format="markdown",
        purpose="personal_review",
        includes_pii=True,
        metadata={
            "user_identifier": user_identifier,
            "sessions_count": len(sessions_dict),
            "interactions_count": total_interactions,
            "total_tokens": total_tokens,
        },
    )

    return str(output_path_obj), manifest


def get_export_stats(corpus_path: str) -> dict:
    """
    Get export statistics from corpus.

    Args:
        corpus_path: Path to HDF5 corpus

    Returns:
        Dict with sessions, interactions, tokens, date range

    Examples:
        >>> stats = get_export_stats("storage/corpus.h5")
        >>> print(f"Sessions: {stats['sessions']}")
    """
    stats = {"sessions": 0, "interactions": 0, "total_tokens": 0, "earliest": None, "latest": None}

    corpus_path_obj = Path(corpus_path)
    if not corpus_path_obj.exists():
        return stats

    with h5py.File(corpus_path, "r") as f:
        if "/interactions" not in f:
            return stats

        group = f["/interactions"]  # type: ignore[index]
        n_interactions = group["session_id"].shape[0]  # type: ignore[index,attr-defined]

        if n_interactions == 0:
            return stats

        # Count unique sessions
        sessions = set()
        timestamps = []
        tokens = []

        for i in range(n_interactions):
            sessions.add(group["session_id"][i].decode("utf-8"))  # type: ignore[index,attr-defined]
            timestamps.append(group["timestamp"][i].decode("utf-8"))  # type: ignore[index,attr-defined]
            tokens.append(int(group["tokens"][i]))  # type: ignore[index]

        stats["sessions"] = len(sessions)  # type: ignore[index]
        stats["interactions"] = n_interactions  # type: ignore[index]
        stats["total_tokens"] = sum(tokens)  # type: ignore[index]
        stats["earliest"] = min(timestamps)  # type: ignore[index]
        stats["latest"] = max(timestamps)  # type: ignore[index]

    return stats


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 backend/fi_exporter.py stats")
        print("  python3 backend/fi_exporter.py session <session_id> <output.md>")
        print("  python3 backend/fi_exporter.py range <start_date> <end_date> <output.h5>")
        print("  python3 backend/fi_exporter.py user <user_id> <output.md>")
        sys.exit(1)

    command = sys.argv[1]
    corpus_path = "storage/corpus.h5"

    if command == "stats":
        stats = get_export_stats(corpus_path)
        sessions = stats['sessions']  # type: ignore[index]
        interactions = stats['interactions']  # type: ignore[index]
        total_tokens = stats['total_tokens']  # type: ignore[index]
        earliest = stats['earliest']  # type: ignore[index]
        latest = stats['latest']  # type: ignore[index]
        print("\n📊 Export Statistics:")
        print(f"   Sessions: {sessions}")
        print(f"   Interactions: {interactions}")
        print(f"   Total Tokens: {total_tokens}")
        print(f"   Date Range: {earliest} → {latest}")

    elif command == "session" and len(sys.argv) >= 4:
        session_id = sys.argv[2]
        output_path = sys.argv[3]
        try:
            path, manifest = export_session_to_markdown(corpus_path, session_id, output_path)
            print(f"✅ Exported session to: {path}")
            print(f"   Manifest: {manifest.export_id}")
            manifest_path = output_path.replace(".md", ".manifest.json")
            with open(manifest_path, "w") as f:
                json.dump(manifest.__dict__, f, indent=2)
            print(f"   Manifest saved: {manifest_path}")
        except Exception as e:
            print(f"❌ Error: {e}")
            sys.exit(1)

    elif command == "range" and len(sys.argv) >= 5:
        start_date = sys.argv[2]
        end_date = sys.argv[3]
        output_path = sys.argv[4]
        try:
            path, manifest = export_range_to_hdf5(corpus_path, output_path, start_date, end_date)
            interactions_count = manifest.metadata['interactions_count']  # type: ignore[index]
            print(f"✅ Exported range to: {path}")
            print(f"   Interactions: {interactions_count}")
            manifest_path = output_path.replace(".h5", ".manifest.json")
            with open(manifest_path, "w") as f:
                json.dump(manifest.__dict__, f, indent=2)
            print(f"   Manifest saved: {manifest_path}")
        except Exception as e:
            print(f"❌ Error: {e}")
            sys.exit(1)

    elif command == "user" and len(sys.argv) >= 4:
        user_id = sys.argv[2]
        output_path = sys.argv[3]
        try:
            path, manifest = export_user_to_markdown(corpus_path, user_id, output_path)
            sessions_count = manifest.metadata['sessions_count']  # type: ignore[index]
            interactions_count = manifest.metadata['interactions_count']  # type: ignore[index]
            print(f"✅ Exported user to: {path}")
            print(f"   Sessions: {sessions_count}")
            print(f"   Interactions: {interactions_count}")
            manifest_path = output_path.replace(".md", ".manifest.json")
            with open(manifest_path, "w") as f:
                json.dump(manifest.__dict__, f, indent=2)
            print(f"   Manifest saved: {manifest_path}")
        except Exception as e:
            print(f"❌ Error: {e}")
            sys.exit(1)

    else:
        print("Invalid command or missing arguments")
        sys.exit(1)
