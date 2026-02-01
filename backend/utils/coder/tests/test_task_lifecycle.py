from __future__ import annotations

import tempfile
import time
import unittest

from ..models.task import Task, TaskStatus
from ..storage.task_storage import TaskStorage


class TestTaskLifecycle(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_file.close()
        self.storage = TaskStorage(self.temp_file.name)

    def tearDown(self):
        import os

        os.unlink(self.temp_file.name)

    def test_task_creation(self):
        task = Task(name="lint", parameters={"repo_root_path": "/tmp"})
        self.assertEqual(task.status, TaskStatus.QUEUED)
        self.assertIsNotNone(task.id)

    def test_task_storage(self):
        task = Task(name="lint")
        self.storage.save_task(task)

        loaded = self.storage.load_task(str(task.id))
        self.assertEqual(loaded.id, task.id)
        self.assertEqual(loaded.name, task.name)

    def test_task_status_transition(self):
        task = Task(name="lint")
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        self.storage.save_task(task)

        loaded = self.storage.load_task(str(task.id))
        self.assertEqual(loaded.status, TaskStatus.RUNNING)

    def test_list_tasks(self):
        task1 = Task(name="lint")
        task2 = Task(name="test")
        self.storage.save_task(task1)
        self.storage.save_task(task2)

        tasks = self.storage.list_tasks()
        self.assertEqual(len(tasks), 2)

        running_tasks = self.storage.list_tasks(status_filter="running")
        self.assertEqual(len(running_tasks), 0)


if __name__ == "__main__":
    unittest.main()
