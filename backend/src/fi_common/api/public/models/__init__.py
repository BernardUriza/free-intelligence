"""Session models package - Data Transfer Objects."""

from .session_models import (
    CheckpointRequest,
    CheckpointResponse,
    DiarizationStatusResponse,
    DoctorFeedbackRequest,
    DoctorFeedbackResponse,
    FinalizeSessionRequest,
    FinalizeSessionResponse,
    SOAPCorrectionModel,
    TranscriptionSourcesModel,
    UpdateSegmentRequest,
)

__all__ = [
    "CheckpointRequest",
    "CheckpointResponse",
    "DiarizationStatusResponse",
    "DoctorFeedbackRequest",
    "DoctorFeedbackResponse",
    "FinalizeSessionRequest",
    "FinalizeSessionResponse",
    "SOAPCorrectionModel",
    "TranscriptionSourcesModel",
    "UpdateSegmentRequest",
]
