from __future__ import annotations

from fastapi import APIRouter, HTTPException
from typing import List
from uuid import UUID

from ..execution.orchestrator import TaskOrchestrator
from ..models.task import Task
from ..observability.metrics import health_monitor, metrics_collector, performance_monitor
from ..storage.task_storage import TaskStorage

router = APIRouter()


def create_api_router(orchestrator: TaskOrchestrator, storage: TaskStorage) -> APIRouter:
    @router.post("/tasks")
    async def create_task(name: str, parameters: dict = None) -> dict:
        """Create and submit a task."""
        parameters = parameters or {}
        task = Task(name=name, parameters=parameters)
        task_id = orchestrator.submit_task(task)
        return {"task_id": task_id}

    @router.post("/pipelines")
    async def create_pipeline(tasks: List[dict]) -> dict:
        """Create and submit a pipeline of tasks."""
        task_objects = [Task(**t) for t in tasks]
        task_ids = orchestrator.submit_pipeline(task_objects)
        return {"task_ids": task_ids}

    @router.get("/tasks/{task_id}")
    async def get_task(task_id: str) -> Task:
        """Get task by ID."""
        task = storage.load_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task

    @router.get("/tasks")
    async def list_tasks(status: str = None) -> List[Task]:
        """List tasks with optional status filter."""
        return storage.list_tasks(status_filter=status)

    @router.delete("/tasks/{task_id}")
    async def cancel_task(task_id: str):
        """Cancel a running task."""
        orchestrator.executor.cancel_task(task_id)
        return {"message": "Task canceled"}

    @router.get("/tasks/{task_id}/logs")
    async def get_task_logs(task_id: str, tail: int = None) -> str:
        """Get task logs."""
        task = storage.load_task(task_id)
        if not task or not task.logs_path:
            raise HTTPException(status_code=404, detail="Logs not found")

        with open(task.logs_path, "r") as f:
            logs = f.read()

        if tail:
            lines = logs.splitlines()
            logs = "\n".join(lines[-tail:])

        return logs

    @router.get("/status")
    async def get_orchestrator_status() -> dict:
        """Get orchestrator status."""
        return orchestrator.get_status()

    @router.get("/metrics")
    async def get_metrics() -> dict:
        """Get system metrics."""
        return {
            "orchestrator": orchestrator.get_metrics(),
            "system": metrics_collector.get_all_metrics(),
        }

    @router.get("/health")
    async def get_health() -> dict:
        """Get system health status."""
        return health_monitor.get_health_report()

    @router.get("/alerts")
    async def get_alerts() -> list:
        """Get active performance alerts."""
        return performance_monitor.get_active_alerts()

    return router