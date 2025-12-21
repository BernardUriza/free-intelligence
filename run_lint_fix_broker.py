#!/usr/bin/env python3
"""
Broker for running lint fix tasks with 100 fixes in a robust way.
This script runs as a separate process that is harder to accidentally cancel.
"""

import os
import sys
import time
import signal
import subprocess
from pathlib import Path


def ignore_signal(signum, frame):
    """Signal handler that ignores cancellation signals"""
    print(f"⚠️  Received signal {signum}, ignoring (task continues running)")
    print("   To stop this process, use: kill -9 <PID>")


def main():
    # Change to project directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Set up signal handlers to ignore common interruption signals
    signal.signal(signal.SIGINT, ignore_signal)  # Ctrl+C
    signal.signal(signal.SIGTERM, ignore_signal) # Termination request
    
    print("🚀 Starting lint fix broker with 100 fixes...")
    print("   PID:", os.getpid())
    print("   This process will ignore cancellation signals")
    print("   To force stop: kill -9", os.getpid())
    print()
    
    # Build the command to run
    cmd = [
        sys.executable, "-m", "fi_cli", "coder", "lint-fix",
        "--max-fixes", "100"
    ]
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root / "backend/src")
    
    try:
        print("🔧 Executing command: python -m fi_cli coder lint-fix --max-fixes 100")
        print()
        
        # Run the process
        result = subprocess.run(
            cmd,
            env=env,
            cwd=project_root,
            stdout=sys.stdout,
            stderr=sys.stderr,
            check=False  # Don't raise exception on non-zero exit
        )
        
        print()
        print("✅ Lint fix task completed with exit code:", result.returncode)
        
        if result.returncode != 0:
            print("⚠️  Task completed with errors (non-zero exit code)")
        else:
            print("🎉 Task completed successfully!")
            
    except KeyboardInterrupt:
        print("\n⚠️  Keyboard interrupt received, but handler is ignoring it")
        print("   Process continues running...")
        # Continue running despite keyboard interrupt
        time.sleep(10)  # Give some time to see if it continues
    
    except Exception as e:
        print(f"❌ Error during execution: {e}")
        
    finally:
        print("\n🏁 Broker process ending")


if __name__ == "__main__":
    main()