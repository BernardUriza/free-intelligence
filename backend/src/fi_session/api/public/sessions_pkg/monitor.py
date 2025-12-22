from __future__ import annotations

from datetime import datetime
from typing import cast

from backend.src.fi_common.logging.logger import get_logger
from backend.validators import validate_session_id
from fastapi import APIRouter, HTTPException, Request, status

router = APIRouter()
logger = get_logger(__name__)


@router.get("/sessions/{session_id}/monitor", status_code=status.HTTP_200_OK)
async def monitor_session_progress(session_id: str, request: Request) -> dict:
    validate_session_id(session_id)
    from backend.models.task_type import TaskType
    from backend.src.fi_storage.infrastructure.hdf5.task_repository import (
        count_task_chunks,
        get_task_metadata,
    )

    accept_header = request.headers.get("accept", "")
    wants_json = "application/json" in accept_header

    try:
        transcription_data = {
            "status": "not_started",
            "progress": 0,
            "chunks_processed": 0,
            "chunks_total": 0,
        }
        diarization_data = {
            "status": "not_started",
            "progress": 0,
            "segment_count": 0,
            "provider": "unknown",
        }
        soap_data = {"status": "not_started"}

        try:
            transcription_meta = get_task_metadata(session_id, TaskType.TRANSCRIPTION) or {}
            total, processed = count_task_chunks(session_id, TaskType.TRANSCRIPTION)
            progress = int((processed / total) * 100) if total > 0 else 0
            status_val = transcription_meta.get(
                "status", "in_progress" if processed > 0 else "pending"
            )
            if processed == total and total > 0:
                status_val = "completed"
            transcription_data = {
                "status": status_val,
                "progress": progress,
                "chunks_processed": processed,
                "chunks_total": total,
                "estimated_seconds_remaining": transcription_meta.get(
                    "estimated_seconds_remaining", 0
                ),
                "provider": transcription_meta.get("provider", "unknown"),
            }
        except ValueError:
            pass

        try:
            diarization_meta = get_task_metadata(session_id, TaskType.DIARIZATION) or {}
            status_val = diarization_meta.get("status", "pending")
            segment_count = diarization_meta.get("segment_count", 0)
            provider = diarization_meta.get("provider", "unknown")
            progress_percent = diarization_meta.get("progress_percent", 0)
            created_at = diarization_meta.get("created_at", "")
            updated_at = diarization_meta.get("updated_at", "")

            elapsed_seconds = 0
            if created_at and updated_at:
                try:
                    created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                    elapsed_seconds = (updated - created).total_seconds()
                except Exception:
                    pass

            if status_val == "completed" and progress_percent == 0:
                progress_percent = 100

            diarization_data = {
                "status": status_val,
                "progress": progress_percent,
                "segment_count": segment_count,
                "provider": provider,
                "elapsed_seconds": elapsed_seconds,
                "created_at": created_at,
            }
        except ValueError:
            pass

        try:
            soap_meta = get_task_metadata(session_id, TaskType.SOAP_GENERATION) or {}
            soap_data = {"status": soap_meta.get("status", "pending")}
        except ValueError:
            pass

        encryption_data = {"status": "not_started", "progress": 0}
        try:
            encryption_meta = get_task_metadata(session_id, TaskType.ENCRYPTION) or {}
            encryption_status = encryption_meta.get("status", "pending")
            encryption_progress = encryption_meta.get("progress_percent", 0)
            encryption_data = {
                "status": encryption_status,
                "progress": encryption_progress,
                "queued_at": encryption_meta.get("queued_at", ""),
            }
        except ValueError:
            pass

        if wants_json:
            return {
                "session_id": session_id,
                "status": diarization_data["status"],
                "progress": diarization_data["progress"],
                "segment_count": diarization_data["segment_count"],
                "error": None,
                "transcription_sources": None,
                "transcription": transcription_data,
                "diarization": diarization_data,
                "soap": soap_data,
                "encryption": encryption_data,
            }

        reset = "\033[0m"
        bold = "\033[1m"
        green = "\033[92m"
        yellow = "\033[93m"
        blue = "\033[94m"
        cyan = "\033[96m"
        red = "\033[91m"

        output_lines: list[str] = []
        output_lines.append(f"\n{bold}{cyan}{'=' * 60}{reset}")
        output_lines.append(f"{bold}{cyan}  Session Monitor: {session_id}{reset}")
        output_lines.append(f"{bold}{cyan}{'=' * 60}{reset}\n")

        status_val = transcription_data["status"]
        progress = cast(int, transcription_data["progress"])
        processed = cast(int, transcription_data["chunks_processed"])
        total = cast(int, transcription_data["chunks_total"])
        if status_val == "not_started":
            output_lines.append(f"{bold}🎙️  TRANSCRIPTION:{reset} {red}NOT STARTED{reset}\n")
        else:
            status_color = (
                green
                if status_val == "completed"
                else yellow
                if status_val == "in_progress"
                else blue
            )
            bar_width = 30
            filled = int((progress / 100) * bar_width)
            bar = f"[{green}{'█' * filled}{reset}{'░' * (bar_width - filled)}]"
            output_lines.append(f"{bold}🎙️  TRANSCRIPTION:{reset}")
            status_text = str(status_val).upper()
            output_lines.append(f"   Status: {status_color}{status_text}{reset}")
            output_lines.append(f"   Progress: {bar} {bold}{progress}%{reset}")
            output_lines.append(f"   Chunks: {bold}{processed}/{total}{reset} completed")
            output_lines.append("")

        status_val = diarization_data["status"]
        segment_count = cast(int, diarization_data["segment_count"])
        provider = diarization_data["provider"]
        progress_percent = cast(int, diarization_data["progress"])
        elapsed_seconds = cast(int, diarization_data.get("elapsed_seconds", 0))
        if status_val == "not_started":
            output_lines.append(f"{bold}👥 DIARIZATION:{reset} {red}NOT STARTED{reset}\n")
        else:
            status_color = (
                green
                if status_val == "completed"
                else yellow
                if status_val == "in_progress"
                else blue
            )
            elapsed_str = (
                f"{elapsed_seconds / 60:.1f}m"
                if elapsed_seconds >= 60
                else f"{elapsed_seconds:.0f}s"
            )
            progress_bar = ""
            if status_val == "in_progress" and progress_percent > 0:
                bar_width = 20
                filled = int((progress_percent / 100) * bar_width)
                progress_bar = (
                    f" {green}{'█' * filled}{reset}{'░' * (bar_width - filled)} {progress_percent}%"
                )
            output_lines.append(f"{bold}👥 DIARIZATION:{reset}")
            status_text = str(status_val).upper()
            output_lines.append(f"   Status: {status_color}{status_text}{reset}{progress_bar}")
            output_lines.append(f"   Provider: {bold}{provider}{reset}")
            output_lines.append(f"   Segments: {bold}{segment_count}{reset}")
            if elapsed_seconds > 0:
                output_lines.append(f"   Duration: {bold}{elapsed_str}{reset}")
            output_lines.append("")

        status_val = soap_data["status"]
        if status_val == "not_started":
            output_lines.append(f"{bold}📋 SOAP GENERATION:{reset} {red}NOT STARTED{reset}\n")
        else:
            status_color = (
                green
                if status_val == "completed"
                else yellow
                if status_val == "in_progress"
                else blue
            )
            output_lines.append(f"{bold}📋 SOAP GENERATION:{reset}")
            status_text = str(status_val).upper()
            output_lines.append(f"   Status: {status_color}{status_text}{reset}")
            output_lines.append("")

        status_val = encryption_data["status"]
        if status_val == "not_started":
            output_lines.append(f"{bold}🔐 ENCRYPTION:{reset} {red}NOT STARTED{reset}\n")
        else:
            status_color = (
                green
                if status_val == "completed"
                else yellow
                if status_val == "in_progress"
                else blue
            )
            progress_val = cast(int, encryption_data["progress"])
            output_lines.append(f"{bold}🔐 ENCRYPTION:{reset}")
            status_text = str(status_val).upper()
            output_lines.append(f"   Status: {status_color}{status_text}{reset}")
            if progress_val > 0:
                output_lines.append(f"   Progress: {bold}{progress_val}%{reset}")
            output_lines.append("")

        output_lines.append(f"{bold}{cyan}{'=' * 60}{reset}\n")
        ascii_output = "\n".join(output_lines)
        return {
            "session_id": session_id,
            "ascii_display": ascii_output,
            "plain_text": ascii_output.replace(reset, "")
            .replace(bold, "")
            .replace(green, "")
            .replace(yellow, "")
            .replace(blue, "")
            .replace(cyan, "")
            .replace(red, ""),
        }

    except Exception as e:
        logger.error("MONITOR_SESSION_FAILED", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to monitor session: {e!s}",
        ) from e
