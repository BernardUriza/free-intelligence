from __future__ import annotations

import argparse
import sys
from typing import List

from ..execution.orchestrator import TaskOrchestrator
from ..models.task import Task
from ..security.validator import SecurityValidator
from ..storage.task_storage import TaskStorage


def main():
    parser = argparse.ArgumentParser(description="FI Coder Task Orchestrator")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Launch task
    launch_parser = subparsers.add_parser("launch", help="Launch a task")
    launch_parser.add_argument("name", help="Task name")
    launch_parser.add_argument("--modules", help="Modules to operate on (for qwen-code tasks)")
    launch_parser.add_argument("--scope", help="Scope for refactor tasks")
    launch_parser.add_argument("--args", help="Custom args for qwen-code")

    # List tasks
    list_parser = subparsers.add_parser("list", help="List tasks")
    list_parser.add_argument("--status", help="Filter by status")

    # Status
    status_parser = subparsers.add_parser("status", help="Get task status")
    status_parser.add_argument("task_id", help="Task ID")

    # Logs
    logs_parser = subparsers.add_parser("logs", help="Get task logs")
    logs_parser.add_argument("task_id", help="Task ID")
    logs_parser.add_argument("--tail", type=int, help="Number of lines to show from end")

    # Cancel
    cancel_parser = subparsers.add_parser("cancel", help="Cancel a task")
    cancel_parser.add_argument("task_id", help="Task ID")

    args = parser.parse_args()

    # Initialize components
    orchestrator = TaskOrchestrator()
    storage = orchestrator.storage
    executor = orchestrator.executor

    if args.command == "launch":
        parameters = {
            "repo_root_path": "/Users/bernardurizaorozco/Documents/free-intelligence"
        }
        if args.modules:
            parameters["modules"] = args.modules
        if args.scope:
            parameters["scope"] = args.scope
        if args.args:
            parameters["args"] = args.args

        task = Task(name=args.name, parameters=parameters)
        task_id = orchestrator.submit_task(task)
        print(f"Task launched: {task_id}")

    elif args.command == "list":
        tasks = storage.list_tasks(status_filter=args.status)
        for task in tasks:
            print(f"{task.id} {task.name} {task.status.value} {task.created_at}")

    elif args.command == "status":
        task = storage.load_task(args.task_id)
        if task:
            print(f"ID: {task.id}")
            print(f"Name: {task.name}")
            print(f"Status: {task.status.value}")
            print(f"Created: {task.created_at}")
            if task.started_at:
                print(f"Started: {task.started_at}")
            if task.completed_at:
                print(f"Completed: {task.completed_at}")
            if task.exit_code is not None:
                print(f"Exit Code: {task.exit_code}")
        else:
            print("Task not found")

    elif args.command == "logs":
        task = storage.load_task(args.task_id)
        if task and task.logs_path:
            with open(task.logs_path, "r") as f:
                logs = f.read()
            if args.tail:
                lines = logs.splitlines()
                logs = "\n".join(lines[-args.tail:])
            print(logs)
        else:
            print("Logs not found")

    elif args.command == "cancel":
        executor.cancel_task(args.task_id)
        print("Task canceled")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()