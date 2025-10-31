"""
Diarization Worker - Dedicated process for CPU-intensive transcription
Card: FI-RELIABILITY-IMPL-003

Architecture:
- RQ (Redis Queue) worker for async job processing
- Semaphore for concurrency control (max 1 job at a time)
- GPU auto-detection (M1 Metal, CUDA, or CPU fallback)
- Parallel chunk processing with ThreadPoolExecutor

Usage:
    # Start worker (development)
    python backend/diarization_worker.py

    # Production (PM2)
    pm2 start backend/diarization_worker.py --name diarization-worker

File: backend/diarization_worker.py
Created: 2025-10-30
"""

import os
import sys
import time
import platform
from pathlib import Path
from rq import Worker, Queue, Connection
from redis import Redis

from backend.logger import get_logger
from backend.diarization_service_v2 import diarize_audio_parallel

logger = get_logger(__name__)

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# Worker configuration
WORKER_NAME = os.getenv("WORKER_NAME", f"diarization-worker-{platform.node()}")
QUEUE_NAME = "diarization"

def detect_device():
    """
    Auto-detect best compute device.

    Returns:
        str: 'mps' (M1/M2), 'cuda' (NVIDIA), or 'cpu'
    """
    # Check for Apple Silicon GPU (M1/M2/M3)
    if platform.processor() == 'arm' and platform.system() == 'Darwin':
        try:
            import torch
            if torch.backends.mps.is_available():
                logger.info("GPU_DETECTED", device="mps", chip=platform.processor())
                return "mps"
        except ImportError:
            pass

    # Check for NVIDIA CUDA
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            logger.info("GPU_DETECTED", device="cuda", gpu=gpu_name)
            return "cuda"
    except ImportError:
        pass

    # Fallback to CPU
    logger.info("GPU_NOT_AVAILABLE", device="cpu", fallback=True)
    return "cpu"


def main():
    """Start RQ worker for diarization jobs."""

    device = detect_device()
    os.environ["WHISPER_DEVICE"] = device

    # Set compute type based on device
    if device == "mps":
        os.environ["WHISPER_COMPUTE_TYPE"] = "float16"
    elif device == "cuda":
        os.environ["WHISPER_COMPUTE_TYPE"] = "float16"
    else:
        os.environ["WHISPER_COMPUTE_TYPE"] = "int8"

    logger.info(
        "WORKER_STARTING",
        name=WORKER_NAME,
        queue=QUEUE_NAME,
        device=device,
        compute_type=os.environ["WHISPER_COMPUTE_TYPE"],
        redis=f"{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    )

    # Connect to Redis
    redis_conn = Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

    try:
        redis_conn.ping()
        logger.info("REDIS_CONNECTED", host=REDIS_HOST, port=REDIS_PORT)
    except Exception as e:
        logger.error("REDIS_CONNECTION_FAILED", error=str(e))
        sys.exit(1)

    # Create queue
    queue = Queue(QUEUE_NAME, connection=redis_conn)

    # Start worker
    with Connection(redis_conn):
        worker = Worker([queue], name=WORKER_NAME)

        logger.info(
            "WORKER_READY",
            worker=WORKER_NAME,
            queues=[QUEUE_NAME],
            pid=os.getpid()
        )

        worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
