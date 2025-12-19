from __future__ import annotations

from ..execution.orchestrator import TaskOrchestrator
from ..storage.task_storage import TaskStorage


class FiCoderService:
    def __init__(self):
        self.orchestrator = TaskOrchestrator()
        self.storage = self.orchestrator.storage

    def get_api_router(self):
        from ..api.router import create_api_router
        return create_api_router(self.orchestrator, self.storage)