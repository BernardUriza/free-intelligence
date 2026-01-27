"""FFmpeg Audio Concatenator - Concrete Implementation.

Implements AudioConcatenatorPort using FFmpeg for audio concatenation.
Handles temporary file management and format conversion.

Thread-safety: Uses tempfile for isolation, stateless.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections.abc import Sequence

import os
from backend.utils.common.logging.logger import get_logger
from pathlib import Path

from ..domain import AudioChunk, AudioFormat
from ..ports.audio_concatenator import AudioConcatenatorPort, ConcatenationError

logger = get_logger(__name__)


class FFmpegConcatenator(AudioConcatenatorPort):
    """FFmpeg-based audio concatenator implementation.

    Uses FFmpeg's concat demuxer for efficient concatenation.
    Outputs to WebM/Opus format for optimal web compatibility.

    Configuration via environment:
        - FFMPEG_PATH: Custom ffmpeg binary path
        - FFMPEG_TIMEOUT: Max execution time in seconds (default: 120)
        - FFMPEG_BITRATE: Output bitrate (default: 128k)
    """

    DEFAULT_TIMEOUT = 120
    DEFAULT_BITRATE = "128k"

    def __init__(self) -> None:
        """Initialize concatenator with configuration from environment."""
        self._ffmpeg_path = os.getenv("FFMPEG_PATH", "ffmpeg")
        self._timeout = int(os.getenv("FFMPEG_TIMEOUT", str(self.DEFAULT_TIMEOUT)))
        self._bitrate = os.getenv("FFMPEG_BITRATE", self.DEFAULT_BITRATE)

    def is_available(self) -> bool:
        """Check if ffmpeg is installed and accessible."""
        return shutil.which(self._ffmpeg_path) is not None

    def concatenate(
        self,
        chunks: Sequence[AudioChunk],
        existing_audio: bytes | None,
        output_format: AudioFormat,
    ) -> bytes:
        """Concatenate audio chunks using FFmpeg.

        Args:
            chunks: Sequence of audio chunks to concatenate (in order)
            existing_audio: Optional existing audio to prepend
            output_format: Desired output format

        Returns:
            Concatenated audio bytes

        Raises:
            ConcatenationError: If concatenation fails
        """
        if not self.is_available():
            raise ConcatenationError(
                f"FFmpeg not found at '{self._ffmpeg_path}'. "
                "Install FFmpeg or set FFMPEG_PATH environment variable."
            )

        if not chunks and not existing_audio:
            logger.warning("CONCAT_NO_INPUT")
            return b""

        try:
            with tempfile.TemporaryDirectory(prefix="ffmpeg_concat_") as tmpdir:
                temp_dir = Path(tmpdir)
                return self._do_concatenate(temp_dir, chunks, existing_audio, output_format)
        except ConcatenationError:
            raise
        except Exception as e:
            logger.error("CONCAT_UNEXPECTED_ERROR", error=str(e), exc_info=True)
            raise ConcatenationError(f"Unexpected error during concatenation: {e}", e)

    def _do_concatenate(
        self,
        temp_dir: Path,
        chunks: Sequence[AudioChunk],
        existing_audio: bytes | None,
        output_format: AudioFormat,
    ) -> bytes:
        """Internal concatenation logic with temp directory."""
        files_to_concat: list[Path] = []

        # Save existing audio if present
        if existing_audio:
            existing_file = temp_dir / "existing.audio"
            existing_file.write_bytes(existing_audio)
            files_to_concat.append(existing_file)
            logger.debug(
                "CONCAT_EXISTING_AUDIO",
                size_bytes=len(existing_audio),
            )

        # Save chunks to temp files
        for chunk in chunks:
            chunk_file = temp_dir / f"chunk_{chunk.index:04d}.{chunk.format.extension}"
            chunk_file.write_bytes(chunk.audio_bytes)
            files_to_concat.append(chunk_file)

        if not files_to_concat:
            logger.warning("CONCAT_NO_FILES")
            return b""

        logger.info(
            "CONCAT_STARTING",
            file_count=len(files_to_concat),
            output_format=output_format.value,
        )

        # Create FFmpeg concat list file
        concat_list_file = temp_dir / "concat_list.txt"
        with open(concat_list_file, "w") as f:
            for audio_file in files_to_concat:
                # FFmpeg requires single quotes and escaped paths
                f.write(f"file '{audio_file}'\n")

        # Determine output settings based on format
        output_file = temp_dir / f"output.{output_format.extension}"
        codec_args = self._get_codec_args(output_format)

        # Build FFmpeg command
        ffmpeg_cmd = [
            self._ffmpeg_path,
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list_file),
            *codec_args,
            str(output_file),
            "-loglevel",
            "error",
            "-y",  # Overwrite output
        ]

        try:
            subprocess.run(
                ffmpeg_cmd,
                check=True,
                timeout=self._timeout,
                capture_output=True,
                text=True,
            )
        except subprocess.TimeoutExpired as e:
            logger.error(
                "FFMPEG_TIMEOUT",
                timeout=self._timeout,
                command=" ".join(ffmpeg_cmd),
            )
            raise ConcatenationError(f"FFmpeg timed out after {self._timeout}s", e)
        except subprocess.CalledProcessError as e:
            logger.error(
                "FFMPEG_FAILED",
                returncode=e.returncode,
                stderr=e.stderr,
                command=" ".join(ffmpeg_cmd),
            )
            raise ConcatenationError(f"FFmpeg failed with code {e.returncode}: {e.stderr}", e)

        # Read output
        if not output_file.exists():
            raise ConcatenationError("FFmpeg did not produce output file")

        output_bytes = output_file.read_bytes()

        if len(output_bytes) == 0:
            raise ConcatenationError("FFmpeg produced empty output file")

        logger.info(
            "CONCAT_SUCCESS",
            input_files=len(files_to_concat),
            output_size_bytes=len(output_bytes),
            output_format=output_format.value,
        )

        return output_bytes

    def _get_codec_args(self, output_format: AudioFormat) -> list[str]:
        """Get FFmpeg codec arguments for output format."""
        if output_format == AudioFormat.WEBM:
            return [
                "-c:a",
                "libopus",
                "-b:a",
                self._bitrate,
            ]
        elif output_format == AudioFormat.MP3:
            return [
                "-c:a",
                "libmp3lame",
                "-b:a",
                self._bitrate,
            ]
        elif output_format == AudioFormat.OGG:
            return [
                "-c:a",
                "libvorbis",
                "-b:a",
                self._bitrate,
            ]
        elif output_format == AudioFormat.WAV:
            return [
                "-c:a",
                "pcm_s16le",
                "-ar",
                "16000",
            ]
        else:
            # Default to copy (no re-encoding)
            return ["-c:a", "copy"]
