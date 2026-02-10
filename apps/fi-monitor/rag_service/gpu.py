"""GPU detection for RAG Service."""

from __future__ import annotations

import sys

import torch

from config import RAG_REQUIRE_GPU


def _detect_device() -> str:
    """Detect best available device (cuda > mps > cpu).

    Exits with error if no GPU found and RAG_REQUIRE_GPU=true (default).
    """
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"[RAG Service] GPU detected: {gpu_name}")
        print(f"[RAG Service] VRAM: {vram_gb:.2f} GB")
        return "cuda"
    elif torch.backends.mps.is_available():
        print("[RAG Service] Apple Silicon GPU detected (MPS)")
        return "mps"
    else:
        if RAG_REQUIRE_GPU:
            # Fail-hard: GPU is mandatory by default
            print("\n" + "=" * 80)
            print("ERROR: No GPU detected - RAG Service requires GPU acceleration")
            print("=" * 80)
            print("\nDIAGNOSIS:")
            print("   - CUDA available: No")
            print("   - MPS available: No")
            print("   - CPU-only mode: Not supported (performance <20ms required)")
            print("\nSOLUTIONS:")
            print("\n   Windows (NVIDIA):")
            print("   1. Install GPU drivers: https://www.nvidia.com/Download/index.aspx")
            print("   2. Install CUDA Toolkit 12.1+: https://developer.nvidia.com/cuda-downloads")
            print("   3. Verify: nvidia-smi (should show GPU)")
            print("   4. Reinstall PyTorch with CUDA: pip install torch --index-url https://download.pytorch.org/whl/cu121")
            print("\n   macOS (Apple Silicon):")
            print("   1. Upgrade to macOS 13+ (Ventura or newer)")
            print("   2. Reinstall PyTorch: pip install --upgrade torch")
            print('   3. Verify: python -c "import torch; print(torch.backends.mps.is_available())"')
            print("\n   Linux (NVIDIA):")
            print("   1. Install GPU drivers: sudo apt install nvidia-driver-535")
            print("   2. Install CUDA: sudo apt install nvidia-cuda-toolkit")
            print("   3. Verify: nvidia-smi")
            print("\nOVERRIDE (Dev/Testing ONLY):")
            print("   export RAG_REQUIRE_GPU=false  # Allow CPU mode (degraded performance)")
            print("\n" + "=" * 80 + "\n")
            sys.exit(1)
        else:
            # Override active - allow CPU with warning
            print("[RAG Service] WARNING: No GPU detected - RAG_REQUIRE_GPU=false override active")
            print("[RAG Service] WARNING: Performance will be degraded (100-300ms vs 20-50ms on GPU)")
            return "cpu"


DEVICE = _detect_device()
