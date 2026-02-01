"""Workflow-related constants (eliminates magic numbers)."""

# Audio Processing
AUDIO_BITRATE_BYTES_PER_SECOND = 12 * 1024  # 12 KB/s (typical compressed audio bitrate)
DEFAULT_AUDIO_DURATION_SECONDS = 60.0  # Fallback if duration undetectable from file

# Workflow Timeouts
WORKFLOW_DISPATCH_TIMEOUT_SECONDS = 300  # 5 minutes (max time to dispatch all tasks)
TASK_EXECUTION_TIMEOUT_SECONDS = 600  # 10 minutes (max time for single task execution)

# Workflow Types (canonical names - MUST match TaskType enum values)
WORKFLOW_DIARIZATION = "DIARIZATION"
WORKFLOW_TRANSCRIPTION = "TRANSCRIPTION"
WORKFLOW_SOAP = "SOAP_GENERATION"
WORKFLOW_EMOTION = "EMOTION_ANALYSIS"
WORKFLOW_ENCRYPTION = "ENCRYPTION"

# Task States (lifecycle)
TASK_PENDING = "pending"
TASK_IN_PROGRESS = "in_progress"
TASK_COMPLETED = "completed"
TASK_FAILED = "failed"

# Routing Thresholds
DIARIZATION_THRESHOLD_SECONDS = 60.0  # Audio >60s requires diarization for speaker attribution
