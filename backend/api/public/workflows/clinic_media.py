"""
Clinic Media Management Workflow - AURITY

Upload and manage multimedia content for waiting room TV displays.
Doctors can upload videos, images, and custom messages for their clinic.

Architecture:
  PUBLIC (this file) → Storage Layer → /storage/clinic_media/

Endpoints:
- POST /workflows/aurity/clinic-media/upload - Upload media file
- GET /workflows/aurity/clinic-media/list - List all clinic media
- DELETE /workflows/aurity/clinic-media/{media_id} - Delete media
- PUT /workflows/aurity/clinic-media/{media_id} - Update media metadata

Author: Bernard Uriza Orozco
Created: 2025-11-18
"""

import hashlib
import time
import uuid
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Storage configuration
MEDIA_STORAGE_PATH = Path("storage/clinic_media")
MEDIA_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/webm", "video/quicktime"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


# ============================================================================
# Request/Response Schemas
# ============================================================================


class ClinicMediaMetadata(BaseModel):
    """Metadata for clinic media content."""

    media_id: str = Field(..., description="Unique media identifier")
    media_type: Literal["image", "video", "message"] = Field(..., description="Type of media")
    title: Optional[str] = Field(None, description="Display title")
    description: Optional[str] = Field(None, description="Description or caption")
    duration: int = Field(default=15000, description="Display duration in milliseconds")
    file_path: Optional[str] = Field(None, description="Relative file path")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    mime_type: Optional[str] = Field(None, description="MIME type")
    uploaded_at: int = Field(
        default_factory=lambda: int(time.time() * 1000),
        description="Upload timestamp (ms)",
    )
    uploaded_by: Optional[str] = Field(None, description="Doctor ID who uploaded (Auth0 sub)")
    clinic_id: Optional[str] = Field(None, description="Clinic identifier")
    is_active: bool = Field(default=True, description="Whether media is active in slider")


class UploadMediaResponse(BaseModel):
    """Response for media upload."""

    success: bool
    media_id: str
    message: str
    metadata: ClinicMediaMetadata


class MediaListResponse(BaseModel):
    """Response for media list."""

    total: int
    media: list[ClinicMediaMetadata]


class UpdateMediaRequest(BaseModel):
    """Request to update media metadata."""

    title: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[int] = None
    is_active: Optional[bool] = None


# ============================================================================
# Storage Helper Functions
# ============================================================================


def save_metadata(metadata: ClinicMediaMetadata) -> None:
    """Save media metadata to JSON file."""
    import json

    metadata_file = MEDIA_STORAGE_PATH / f"{metadata.media_id}.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata.model_dump(), f, indent=2, ensure_ascii=False)


def load_metadata(media_id: str) -> Optional[ClinicMediaMetadata]:
    """Load media metadata from JSON file."""
    import json

    metadata_file = MEDIA_STORAGE_PATH / f"{media_id}.json"
    if not metadata_file.exists():
        return None

    with open(metadata_file, encoding="utf-8") as f:
        data = json.load(f)
        return ClinicMediaMetadata(**data)


def delete_media_files(media_id: str) -> None:
    """Delete media file and metadata."""
    metadata = load_metadata(media_id)
    if not metadata:
        return

    # Delete media file if it exists
    if metadata.file_path:
        file_path = MEDIA_STORAGE_PATH / metadata.file_path
        if file_path.exists():
            file_path.unlink()

    # Delete metadata file
    metadata_file = MEDIA_STORAGE_PATH / f"{media_id}.json"
    if metadata_file.exists():
        metadata_file.unlink()


def list_all_media() -> list[ClinicMediaMetadata]:
    """List all media metadata."""
    import json

    media_list = []
    for metadata_file in MEDIA_STORAGE_PATH.glob("*.json"):
        with open(metadata_file, encoding="utf-8") as f:
            data = json.load(f)
            media_list.append(ClinicMediaMetadata(**data))

    # Sort by upload time (newest first)
    media_list.sort(key=lambda m: m.uploaded_at, reverse=True)
    return media_list


# ============================================================================
# Endpoints
# ============================================================================


@router.post(
    "/clinic-media/upload",
    response_model=UploadMediaResponse,
    tags=["Clinic Media"],
    summary="Upload media for TV display",
    description="""
    Upload images, videos, or text messages for waiting room TV display.

    **Supported formats**:
    - Images: JPEG, PNG, GIF, WebP (max 50MB)
    - Videos: MP4, WebM, QuickTime (max 50MB)
    - Messages: Plain text (no file upload)

    **Data sovereignty**: All media stored locally in `storage/clinic_media/`
    """,
)
async def upload_clinic_media(
    file: Optional[UploadFile] = File(None),
    media_type: str = Form(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    duration: int = Form(15000),
    message_content: Optional[str] = Form(None),
    clinic_id: Optional[str] = Form(None),
    doctor_id: Optional[str] = Form(None),
) -> UploadMediaResponse:
    """
    Upload clinic media for TV display.

    For images/videos: Provide file
    For messages: Provide message_content (no file)
    """
    try:
        media_id = str(uuid.uuid4())

        # Handle text messages (no file upload)
        if media_type == "message":
            if not message_content:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="message_content is required for message type",
                )

            metadata = ClinicMediaMetadata(
                media_id=media_id,
                media_type="message",
                title=title or "Mensaje Personalizado",
                description=message_content,
                duration=duration,
                uploaded_by=doctor_id,
                clinic_id=clinic_id,
            )

            save_metadata(metadata)

            logger.info(
                "Uploaded clinic message",
                media_id=media_id,
                doctor_id=doctor_id,
                clinic_id=clinic_id,
            )

            return UploadMediaResponse(
                success=True,
                media_id=media_id,
                message="Message uploaded successfully",
                metadata=metadata,
            )

        # Handle file uploads (image/video)
        if not file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is required for image/video uploads",
            )

        # Validate file size
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large (max {MAX_FILE_SIZE // 1024 // 1024}MB)",
            )

        # Validate MIME type
        if media_type == "image":
            if file.content_type not in ALLOWED_IMAGE_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid image type. Allowed: {ALLOWED_IMAGE_TYPES}",
                )
        elif media_type == "video":
            if file.content_type not in ALLOWED_VIDEO_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid video type. Allowed: {ALLOWED_VIDEO_TYPES}",
                )

        # Generate filename with hash for deduplication
        file_hash = hashlib.sha256(contents).hexdigest()[:16]
        file_extension = Path(file.filename or "file").suffix
        safe_filename = f"{media_id}_{file_hash}{file_extension}"

        # Save file
        file_path = MEDIA_STORAGE_PATH / safe_filename
        with open(file_path, "wb") as f:
            f.write(contents)

        # Create metadata
        metadata = ClinicMediaMetadata(
            media_id=media_id,
            media_type=media_type,  # type: ignore
            title=title or file.filename,
            description=description,
            duration=duration,
            file_path=safe_filename,
            file_size=len(contents),
            mime_type=file.content_type,
            uploaded_by=doctor_id,
            clinic_id=clinic_id,
        )

        save_metadata(metadata)

        logger.info(
            "Uploaded clinic media",
            media_id=media_id,
            media_type=media_type,
            file_size=len(contents),
            doctor_id=doctor_id,
            clinic_id=clinic_id,
        )

        return UploadMediaResponse(
            success=True,
            media_id=media_id,
            message=f"{media_type.capitalize()} uploaded successfully",
            metadata=metadata,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to upload clinic media", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload media: {e!s}",
        )


@router.get(
    "/clinic-media/list",
    response_model=MediaListResponse,
    tags=["Clinic Media"],
    summary="List all clinic media",
)
async def list_clinic_media(
    clinic_id: Optional[str] = None,
    active_only: bool = True,
) -> MediaListResponse:
    """
    List all clinic media content.

    Filter by clinic_id if provided.
    Filter by is_active if active_only=True.
    """
    try:
        media_list = list_all_media()

        # Filter by clinic_id
        if clinic_id:
            media_list = [m for m in media_list if m.clinic_id == clinic_id]

        # Filter by active status
        if active_only:
            media_list = [m for m in media_list if m.is_active]

        return MediaListResponse(total=len(media_list), media=media_list)

    except Exception as e:
        logger.error("Failed to list clinic media", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list media: {e!s}",
        )


@router.put(
    "/clinic-media/{media_id}",
    response_model=ClinicMediaMetadata,
    tags=["Clinic Media"],
    summary="Update media metadata",
)
async def update_clinic_media(media_id: str, request: UpdateMediaRequest) -> ClinicMediaMetadata:
    """
    Update media metadata (title, description, duration, active status).
    """
    try:
        metadata = load_metadata(media_id)
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Media {media_id} not found",
            )

        # Update fields
        if request.title is not None:
            metadata.title = request.title
        if request.description is not None:
            metadata.description = request.description
        if request.duration is not None:
            metadata.duration = request.duration
        if request.is_active is not None:
            metadata.is_active = request.is_active

        save_metadata(metadata)

        logger.info("Updated clinic media", media_id=media_id, updates=request.model_dump())

        return metadata

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update clinic media", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update media: {e!s}",
        )


@router.delete(
    "/clinic-media/{media_id}",
    tags=["Clinic Media"],
    summary="Delete clinic media",
)
async def delete_clinic_media(media_id: str) -> dict:
    """
    Delete clinic media and associated files.
    """
    try:
        metadata = load_metadata(media_id)
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Media {media_id} not found",
            )

        delete_media_files(media_id)

        logger.info("Deleted clinic media", media_id=media_id)

        return {"success": True, "message": f"Media {media_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete clinic media", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete media: {e!s}",
        )


@router.get(
    "/clinic-media/file/{filename}",
    tags=["Clinic Media"],
    summary="Serve media file",
    description="""
    Serve uploaded media files (images/videos) for TV display.

    **Data sovereignty**: Files served from local `storage/clinic_media/`
    """,
)
async def serve_clinic_media_file(filename: str) -> FileResponse:
    """
    Serve media file by filename.

    This endpoint serves the actual image/video files uploaded by doctors.
    Files are stored locally and never leave the clinic's infrastructure.
    """
    try:
        file_path = MEDIA_STORAGE_PATH / filename

        # Security: Prevent directory traversal attacks
        if ".." in filename or filename.startswith("/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid filename",
            )

        # Check file exists
        if not file_path.exists():
            logger.warning("Media file not found", filename=filename)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Media file not found: {filename}",
            )

        logger.info("Serving media file", filename=filename, size=file_path.stat().st_size)

        # FileResponse automatically detects content-type from extension
        return FileResponse(
            path=file_path,
            media_type=None,  # Auto-detect
            filename=filename,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to serve media file", filename=filename, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to serve file: {e!s}",
        )
