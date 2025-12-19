from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime
from typing import Any, Dict

from ..config.policies import (
    EXECUTION_POLICY,
    LOGGING_POLICY,
    MODEL_POLICY,
    REPO_ROOT_PATH,
    SCOPE_POLICY,
    WORKSPACE_POLICY,
)
from ..models.task import ExecutionFingerprint, Task, TaskStatus
from ..security.validator import SecurityValidator
from ..storage.task_storage import TaskStorage
from ..utils.logging import get_logger

logger = get_logger(__name__)


class TaskExecutor:
    def __init__(self, storage: TaskStorage, security: SecurityValidator):
        self.storage = storage
        self.security = security
        self.running_tasks: Dict[str, subprocess.Popen] = {}
        self._lock = threading.Lock()

    def submit_task(self, task: Task) -> str:
        """Submit task for execution."""
        if not self.security.validate_task_name(task.name):
            raise ValueError(f"Task {task.name} not in allowlist")

        # Validate parameters against schema and security
        self.security.validate_parameters(task.name, task.parameters)

        # Resolve command
        task.command = self._resolve_command(task)

        task.status = TaskStatus.QUEUED
        self.storage.save_task(task)

        # Start in background
        threading.Thread(target=self._execute_task, args=(task,), daemon=False).start()

        logger.info("task_submitted", task_id=str(task.id), task_name=task.name)
        return str(task.id)

    def _execute_task(self, task: Task):
        """Execute task in background."""
        try:
            # Calculate execution fingerprint before execution
            task.execution_fingerprint = self._calculate_fingerprint(task)
            self.storage.save_task(task)

            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            self.storage.save_task(task)

            # Resolve command
            command = self._resolve_command(task)

            # Setup logging
            log_file = self._setup_logging(task)

            # Execute
            with open(log_file, "w") as log_f:
                # Build command as list for security
                command_list = self._build_command_list(task)
                process = subprocess.Popen(
                    command_list,
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    cwd=task.parameters.get("repo_root_path", REPO_ROOT_PATH),
                    env=self.security.sanitize_environment(os.environ.copy()),
                    preexec_fn=os.setsid,
                )

            with self._lock:
                self.running_tasks[str(task.id)] = process

            # Wait for completion or timeout
            timeout = task.timeout_seconds or EXECUTION_POLICY["default_timeout_seconds"]
            try:
                return_code = process.wait(timeout=timeout)
                task.exit_code = return_code
                task.status = TaskStatus.SUCCEEDED if return_code == 0 else TaskStatus.FAILED
            except subprocess.TimeoutExpired:
                self._kill_task(task.id)
                task.status = TaskStatus.TIMED_OUT
                task.error_message = "Task timed out"

            task.completed_at = datetime.now()
            task.logs_path = log_file
            self.storage.save_task(task)

            logger.info(
                "task_completed",
                task_id=str(task.id),
                status=task.status.value,
                exit_code=task.exit_code,
            )

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.completed_at = time.time()
            self.storage.save_task(task)
            logger.error("task_execution_failed", task_id=str(task.id), error=str(e))

    def _calculate_fingerprint(self, task: Task) -> ExecutionFingerprint:
        """Calculate execution fingerprint for task."""
        import hashlib

        fingerprint = ExecutionFingerprint()

        # Qwen-code version (if applicable)
        if "qwen-code" in task.name:
            try:
                result = subprocess.run(["qwen-code", "--version"], capture_output=True, text=True, timeout=5)
                fingerprint.qwen_code_version = result.stdout.strip() if result.returncode == 0 else None
            except:
                fingerprint.qwen_code_version = None

        # Model parameters
        fingerprint.model_parameters = MODEL_POLICY.copy()

        # Workspace fingerprint
        try:
            result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT_PATH, capture_output=True, text=True, timeout=5)
            fingerprint.workspace_commit = result.stdout.strip() if result.returncode == 0 else None
            result = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_ROOT_PATH, capture_output=True, text=True, timeout=5)
            fingerprint.workspace_dirty = bool(result.stdout.strip())
        except:
            fingerprint.workspace_commit = None
            fingerprint.workspace_dirty = False

        # Touched files (initially empty)
        fingerprint.touched_files = []

        # Operated paths
        fingerprint.operated_paths = [task.parameters.get("repo_root_path", REPO_ROOT_PATH)]

        # Working directory
        fingerprint.working_directory = os.getcwd()

        # Scope restrictions
        fingerprint.scope_restrictions = SCOPE_POLICY.copy()

        # Python version
        fingerprint.python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

        # Dependencies fingerprint
        try:
            with open(os.path.join(REPO_ROOT_PATH, "requirements.txt"), "r") as f:
                reqs = f.read()
                fingerprint.dependencies_fingerprint = hashlib.sha256(reqs.encode()).hexdigest()[:16]
        except:
            fingerprint.dependencies_fingerprint = None

        return fingerprint

    def _build_command_list(self, task: Task) -> List[str]:
        """Build command as list for secure execution."""
        from ..config.policies import COMMAND_TEMPLATES

        template = COMMAND_TEMPLATES[task.name]
        command_str = template.format(**task.parameters)
        
        # Use shlex for proper parsing
        import shlex
        return shlex.split(command_str)

    def _resolve_command(self, task: Task) -> str:
        """Resolve command template with parameters."""
        from ..config.policies import COMMAND_TEMPLATES

        template = COMMAND_TEMPLATES[task.name]
        return template.format(**task.parameters)

    def _setup_logging(self, task: Task) -> str:
        """Setup log file for task."""
        log_dir = LOGGING_POLICY["log_directory"]
        os.makedirs(log_dir, exist_ok=True)
        return os.path.join(log_dir, f"{task.id}.log")

    def cancel_task(self, task_id: str):
        """Cancel running task."""
        with self._lock:
            if task_id in self.running_tasks:
                self._kill_task(task_id)
                task = self.storage.load_task(task_id)
                if task:
                    task.status = TaskStatus.CANCELED
                    task.completed_at = time.time()
                    self.storage.save_task(task)
                logger.info("task_canceled", task_id=task_id)

    def _kill_task(self, task_id: str):
        """Kill task process."""
        if task_id in self.running_tasks:
            process = self.running_tasks[task_id]
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                process.wait(timeout=5)
            except (subprocess.TimeoutExpired, ProcessLookupError):
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass