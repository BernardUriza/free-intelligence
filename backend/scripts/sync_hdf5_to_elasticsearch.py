#!/usr/bin/env python3.14
"""Sync HDF5 corpus to Elasticsearch (one-time migration).

Migrates all audio transcription events from storage/corpus.h5 to Elasticsearch.

Usage:
    PYTHONPATH=backend/src python3.14 backend/scripts/sync_hdf5_to_elasticsearch.py

Requirements:
    - Elasticsearch running on localhost:9200 (or ELASTICSEARCH_URL env var)
    - storage/corpus.h5 exists with transcription data

Author: Claude Sonnet 4.5 (El Revisor Agresivo)
Created: 2026-01-31
Purpose: Fix O(N) search by migrating to Elasticsearch
"""

import os
import sys
from pathlib import Path

# Add backend/src to Python path
backend_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(backend_src))

from elasticsearch import Elasticsearch
from backend.repositories.hdf5_memory_store import HDF5MemoryStore
from backend.repositories.elasticsearch_memory_store import ElasticsearchMemoryStore
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)


def main():
    """Sync all HDF5 transcriptions to Elasticsearch."""
    # Configuration
    corpus_path = os.getenv("CORPUS_PATH", "storage/corpus.h5")
    elasticsearch_url = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")

    logger.info(
        "SYNC_STARTED",
        corpus_path=corpus_path,
        elasticsearch_url=elasticsearch_url,
    )

    # Check corpus exists
    if not Path(corpus_path).exists():
        logger.error("CORPUS_NOT_FOUND", path=corpus_path)
        print(f"❌ Corpus not found: {corpus_path}")
        return 1

    # Initialize stores
    try:
        hdf5_store = HDF5MemoryStore(corpus_path=corpus_path)
        es_client = Elasticsearch([elasticsearch_url])
        es_store = ElasticsearchMemoryStore(es_client=es_client)
    except Exception as e:
        logger.error("STORE_INITIALIZATION_ERROR", error=str(e))
        print(f"❌ Failed to initialize stores: {e}")
        return 1

    # Get unique doctor IDs from HDF5
    try:
        import h5py

        doctor_ids = set()
        with h5py.File(corpus_path, "r") as f:
            if "sessions" not in f:
                logger.warning("NO_SESSIONS_GROUP", path=corpus_path)
                print("⚠️  No sessions group in corpus")
                return 0

            sessions_group = f["sessions"]
            for session_id in sessions_group:
                session = sessions_group[session_id]

                # Extract doctor_id
                for attr_key in ["doctor_id", "owner_id", "user_id"]:
                    if attr_key in session.attrs:
                        raw_value = session.attrs[attr_key]
                        if isinstance(raw_value, bytes):
                            doctor_id = raw_value.decode("utf-8", errors="replace")
                        elif isinstance(raw_value, str):
                            doctor_id = raw_value
                        else:
                            continue  # Invalid type

                        doctor_ids.add(doctor_id)
                        break

        logger.info("DISCOVERED_DOCTORS", count=len(doctor_ids), doctor_ids=list(doctor_ids))
        print(f"📊 Found {len(doctor_ids)} unique doctors")

    except Exception as e:
        logger.error("DOCTOR_DISCOVERY_ERROR", error=str(e))
        print(f"❌ Failed to discover doctors: {e}")
        return 1

    # Sync each doctor
    total_success = 0
    total_errors = 0

    for i, doctor_id in enumerate(sorted(doctor_ids), 1):
        logger.info(
            "SYNCING_DOCTOR",
            doctor_id=doctor_id,
            progress=f"{i}/{len(doctor_ids)}",
        )
        print(f"\n[{i}/{len(doctor_ids)}] Syncing {doctor_id}...")

        try:
            # Get all events from HDF5
            events, total_count = hdf5_store.get_audio_events(
                doctor_id=doctor_id,
                limit=100000,  # Large limit to get all events
                offset=0,
            )

            if not events:
                logger.info("NO_EVENTS_FOR_DOCTOR", doctor_id=doctor_id)
                print(f"  ℹ️  No events found for {doctor_id}")
                continue

            logger.info(
                "FETCHED_EVENTS",
                doctor_id=doctor_id,
                count=len(events),
                total=total_count,
            )
            print(f"  📥 Fetched {len(events)} events from HDF5")

            # Bulk index into Elasticsearch
            success_count, error_count = es_store.bulk_index_audio_events(
                doctor_id=doctor_id,
                events=events,
            )

            total_success += success_count
            total_errors += error_count

            logger.info(
                "INDEXED_EVENTS",
                doctor_id=doctor_id,
                success=success_count,
                errors=error_count,
            )
            print(f"  ✅ Indexed {success_count}/{len(events)} events")

            if error_count > 0:
                print(f"  ⚠️  {error_count} errors during indexing")

        except Exception as e:
            logger.error(
                "SYNC_DOCTOR_ERROR",
                doctor_id=doctor_id,
                error=str(e),
                exc_info=True,
            )
            print(f"  ❌ Error syncing {doctor_id}: {e}")
            continue

    # Summary
    logger.info(
        "SYNC_COMPLETED",
        total_success=total_success,
        total_errors=total_errors,
    )
    print("\n" + "=" * 60)
    print(f"✅ Sync completed")
    print(f"   Total indexed: {total_success}")
    print(f"   Total errors: {total_errors}")
    print("=" * 60)

    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
