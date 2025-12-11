"""Checkpoint Adapters - Concrete Implementations.

Adapters implement the ports (interfaces) defined in the ports layer.
They handle all external dependencies (HDF5, FFmpeg, filesystem).

Clean Architecture: Adapters are the outermost layer.
They can depend on domain and ports, but nothing depends on them.
"""

from .ffmpeg_concatenator import FFmpegConcatenator
from .hdf5_repository import HDF5AudioRepository

__all__ = [
    "FFmpegConcatenator",
    "HDF5AudioRepository",
]
