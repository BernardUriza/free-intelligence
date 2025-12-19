from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from queue import PriorityQueue
from typing import Dict, List, Optional

from ..config.policies import EXECUTION_POLICY
from ..execution.executor import TaskExecutor
from ..models.task import Task, TaskStatus
from ..observability.metrics import health_monitor, metrics_collector, performance_monitor
from ..security.validator import SecurityValidator
from ..storage.task_storage import TaskStorage
from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(order=True)
class PrioritizedTask:
    """Task with priority for queue ordering."""
    priority: int
    task: Task = field(compare=False)
    submitted_at: float = field(default_factory=time.time, compare=False)


class TaskOrchestrator:
    """Advanced task orchestrator with metrics, priorities, and health monitoring."""

    def __init__(self):
        self.storage = TaskStorage()
        self.security = SecurityValidator()
        self.executor = TaskExecutor(self.storage, self.security)

        # Priority queue for tasks (lower number = higher priority)
        self.task_queue: PriorityQueue[PrioritizedTask] = PriorityQueue()
        self.active_tasks: Dict[str, Task] = {}
        self.completed_tasks: deque = deque(maxlen=1000)  # Keep last 1000 for metrics

        self.max_concurrent = EXECUTION_POLICY["max_concurrent_tasks"]
        self._lock = threading.RLock()  # Reentrant lock for nested calls
        self._stop_event = threading.Event()
        self._workers: List[threading.Thread] = []

        # Metrics
        self.metrics = {
            "tasks_submitted": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "tasks_cancelled": 0,
            "tasks_timed_out": 0,
            "avg_execution_time": 0.0,
            "total_execution_time": 0.0,
            "queue_wait_time": 0.0,
            "start_time": time.time(),
        }

        # Priority levels (lower = higher priority)
        self.PRIORITY_LEVELS = {
            "high": 0,      # Critical tasks
            "normal": 1,    # Regular tasks
            "low": 2,       # Background tasks
        }

        # Start worker threads
        self._start_workers()

        # Start metrics collector
        self._metrics_thread = threading.Thread(target=self._collect_metrics, daemon=True)
        self._metrics_thread.start()

        # Register health checks
        health_monitor.register_health_check("orchestrator", self._orchestrator_health_check)

        logger.info("orchestrator_initialized", max_concurrent=self.max_concurrent)

    def submit_task(self, task: Task, priority: str = "normal") -> str:
        """Submit task with priority."""
        task_id = self.executor.submit_task(task)

        prio_level = self.PRIORITY_LEVELS.get(priority, 1)
        prioritized_task = PrioritizedTask(prio_level, task)

        with self._lock:
            self.task_queue.put(prioritized_task)
            self.metrics["tasks_submitted"] += 1
            metrics_collector.increment_counter("tasks_submitted", tags={"priority": priority})

        logger.info("task_queued", task_id=task_id, priority=priority, queue_size=self.task_queue.qsize())
        return task_id

    def submit_pipeline(self, tasks: List[Task], priority: str = "normal") -> List[str]:
        """Submit pipeline of tasks with dependencies."""
        task_ids = []
        for task in tasks:
            task_id = self.submit_task(task, priority)
            task_ids.append(task_id)
        return task_ids

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a queued or running task."""
        with self._lock:
            # Check if running
            if task_id in self.active_tasks:
                self.executor.cancel_task(task_id)
                self.metrics["tasks_cancelled"] += 1
                return True

            # Check if queued (this is complex with PriorityQueue)
            # For now, just mark for cancellation in storage
            task = self.storage.load_task(task_id)
            if task and task.status == TaskStatus.QUEUED:
                task.status = TaskStatus.CANCELED
                self.storage.save_task(task)
                self.metrics["tasks_cancelled"] += 1
                return True

        return False

    def get_task_status(self, task_id: str) -> Optional[Task]:
        """Get detailed task status."""
        return self.storage.load_task(task_id)

    def get_queue_status(self) -> Dict:
        """Get detailed queue status."""
        with self._lock:
            queued_by_priority = defaultdict(int)
            for _ in range(self.task_queue.qsize()):
                try:
                    item = self.task_queue.get_nowait()
                    queued_by_priority[f"priority_{item.priority}"] += 1
                    self.task_queue.put(item)  # Put back
                except:
                    break

            return {
                "active_tasks": len(self.active_tasks),
                "queued_tasks": self.task_queue.qsize(),
                "queued_by_priority": dict(queued_by_priority),
                "max_concurrent": self.max_concurrent,
                "workers_alive": sum(1 for w in self._workers if w.is_alive()),
            }

    def get_metrics(self) -> Dict:
        """Get orchestrator metrics."""
        with self._lock:
            uptime = time.time() - self.metrics["start_time"]
            base_metrics = {
                **self.metrics,
                "uptime_seconds": uptime,
                "tasks_per_second": self.metrics["tasks_completed"] / uptime if uptime > 0 else 0,
                "success_rate": (
                    self.metrics["tasks_completed"] /
                    max(1, self.metrics["tasks_completed"] + self.metrics["tasks_failed"])
                ),
                "queue_depth": self.task_queue.qsize(),
                "active_workers": len(self.active_tasks),
            }

            # Add metrics to global collector
            for key, value in base_metrics.items():
                if isinstance(value, (int, float)):
                    metrics_collector.set_gauge(f"orchestrator_{key}", value)

            return base_metrics

    def health_check(self) -> Dict:
        """Comprehensive health check."""
        status = self.get_queue_status()
        metrics = self.get_metrics()

        # Check if system is healthy
        healthy = (
            status["workers_alive"] == self.max_concurrent and
            metrics["tasks_per_second"] >= 0  # Basic sanity check
        )

        return {
            "healthy": healthy,
            "status": status,
            "metrics": metrics,
            "timestamp": time.time(),
        }

    def graceful_shutdown(self, timeout: float = 30.0):
        """Gracefully shutdown orchestrator."""
        logger.info("orchestrator_shutdown_initiated", timeout=timeout)

        self._stop_event.set()

        # Wait for active tasks to complete
        start_time = time.time()
        while self.active_tasks and (time.time() - start_time) < timeout:
            time.sleep(0.1)

        # Cancel remaining tasks
        with self._lock:
            for task_id in list(self.active_tasks.keys()):
                self.cancel_task(task_id)

        logger.info("orchestrator_shutdown_complete")

    def _start_workers(self):
        """Start worker threads."""
        for i in range(self.max_concurrent):
            worker = threading.Thread(target=self._worker_loop, name=f"orchestrator-worker-{i}", daemon=True)
            worker.start()
            self._workers.append(worker)

    def _worker_loop(self):
        """Main worker loop with error handling and recovery."""
        while not self._stop_event.is_set():
            try:
                # Get next task with timeout
                try:
                    prioritized_task = self.task_queue.get(timeout=1.0)
                    task = prioritized_task.task
                except:
                    continue

                # Execute task
                with self._lock:
                    self.active_tasks[task.id] = task

                start_time = time.time()
                try:
                    self.executor._execute_task(task)

                    # Update metrics
                    execution_time = time.time() - start_time
                    with self._lock:
                        self.metrics["tasks_completed"] += 1
                        self.metrics["total_execution_time"] += execution_time
                        self.metrics["avg_execution_time"] = (
                            self.metrics["total_execution_time"] / self.metrics["tasks_completed"]
                        )
                        self.completed_tasks.append({
                            "task_id": task.id,
                            "execution_time": execution_time,
                            "completed_at": time.time(),
                        })

                    metrics_collector.record_histogram("task_execution_time", execution_time, {"task_name": task.name})
                    metrics_collector.increment_counter("tasks_completed", tags={"task_name": task.name})

                except Exception as e:
                    with self._lock:
                        self.metrics["tasks_failed"] += 1
                    metrics_collector.increment_counter("tasks_failed", tags={"task_name": task.name, "error": str(e)})
                    logger.error("task_execution_error", task_id=task.id, error=str(e))

                finally:
                    with self._lock:
                        self.active_tasks.pop(task.id, None)
                    self.task_queue.task_done()

            except Exception as e:
                logger.error("worker_error", error=str(e))
                time.sleep(1)  # Prevent tight error loops

    def _collect_metrics(self):
        """Background metrics collection."""
        while not self._stop_event.is_set():
            try:
                # Clean old completed tasks (keep last 24 hours)
                cutoff = time.time() - 86400
                with self._lock:
                    while self.completed_tasks and self.completed_tasks[0]["completed_at"] < cutoff:
                        self.completed_tasks.popleft()

                # Log periodic metrics
                if int(time.time()) % 300 == 0:  # Every 5 minutes
                    metrics = self.get_metrics()
                    logger.info("orchestrator_metrics", **metrics)

            except Exception as e:
                logger.error("metrics_collection_error", error=str(e))

            time.sleep(60)  # Collect every minute

    def _orchestrator_health_check(self) -> Dict[str, Any]:
        """Health check for orchestrator."""
        status = self.get_queue_status()
        metrics = self.get_metrics()

        # Determine health status
        healthy_workers = status["workers_alive"] == self.max_concurrent
        reasonable_queue = status["queued_tasks"] < self.max_concurrent * 2
        good_success_rate = metrics["success_rate"] > 0.8

        if healthy_workers and reasonable_queue and good_success_rate:
            health_status = "healthy"
            message = "Orchestrator operating normally"
        elif healthy_workers and reasonable_queue:
            health_status = "degraded"
            message = f"Low success rate: {metrics['success_rate']:.2%}"
        else:
            health_status = "unhealthy"
            message = "Orchestrator has issues"

        return {
            "status": health_status,
            "message": message,
            "metrics": {
                "active_tasks": status["active_tasks"],
                "queued_tasks": status["queued_tasks"],
                "workers_alive": status["workers_alive"],
                "success_rate": metrics["success_rate"],
                "avg_execution_time": metrics["avg_execution_time"],
            }
        }