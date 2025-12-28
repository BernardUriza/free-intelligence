#!/usr/bin/env python3
"""
Broker for running lint fix tasks with 100 fixes in a robust way.
This script runs as a separate process that is harder to accidentally cancel.
This version logs output to a file for review after completion.
"""

import os
import sys
import time
import signal
import subprocess
from pathlib import Path
from datetime import datetime


def ignore_signal(signum, frame):
    """Signal handler that ignores cancellation signals"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open('broker_output.log', 'a') as f:
        f.write(f"[{timestamp}] ⚠️  Received signal {signum}, ignoring (task continues running)\n")
        f.write(f"   To stop this process, use: kill -9 {os.getpid()}\n")
        f.flush()


def main():
    # Change to project directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with open('broker_output.log', 'a') as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"[{timestamp}] 🚀 Starting lint fix broker with 200 fixes...\n")
        f.write(f"   PID: {os.getpid()}\n")
        f.write(f"   This process will ignore cancellation signals\n")
        f.write(f"   To force stop: kill -9 {os.getpid()}\n")
        f.write(f"   Started command: python -m fi_cli coder lint-fix --max-fixes 200\n")
        f.write(f"{'='*60}\n")
        f.flush()
    
    # Set up signal handlers to ignore common interruption signals
    signal.signal(signal.SIGINT, ignore_signal)  # Ctrl+C
    signal.signal(signal.SIGTERM, ignore_signal) # Termination request
    
    # Build the command to run
    cmd = [
        sys.executable, "-m", "fi_cli", "coder", "lint-fix",
        "--max-fixes", "200"
    ]
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root / "backend/src")
    
    try:
        with open('broker_output.log', 'a') as f:
            f.write(f"[{timestamp}] 🔧 Executing command: python -m fi_cli coder lint-fix --max-fixes 100\n")
            f.flush()
        
        # Run the process, capturing output to the log file
        with open('broker_output.log', 'a') as log_file:
            result = subprocess.run(
                cmd,
                env=env,
                cwd=project_root,
                stdout=log_file,
                stderr=log_file,
                check=False  # Don't raise exception on non-zero exit
            )
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open('broker_output.log', 'a') as f:
            f.write(f"\n[{timestamp}] ✅ Lint fix task completed with exit code: {result.returncode}\n")
            
            if result.returncode != 0:
                f.write(f"[{timestamp}] ⚠️  Task completed with errors (non-zero exit code)\n")
            else:
                f.write(f"[{timestamp}] 🎉 Task completed successfully!\n")
            
            f.write(f"{'='*60}\n")
            f.write(f"[{timestamp}] 🏁 Broker process ending\n")
            f.write(f"{'='*60}\n")
            f.flush()
        
    except KeyboardInterrupt:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open('broker_output.log', 'a') as f:
            f.write(f"\n[{timestamp}] ⚠️  Keyboard interrupt received, but handler is ignoring it\n")
            f.write(f"[{timestamp}]    Process continues running...\n")
            f.flush()
        # Continue running despite keyboard interrupt
        time.sleep(10)  # Give some time to see if it continues
    
    except Exception as e:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open('broker_output.log', 'a') as f:
            f.write(f"\n[{timestamp}] ❌ Error during execution: {e}\n")
            f.flush()
        
    finally:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open('broker_output.log', 'a') as f:
            f.write(f"[{timestamp}] 🏁 Broker process ending\n")
            f.write(f"{'='*60}\n")
            f.flush()


if __name__ == "__main__":
    main()