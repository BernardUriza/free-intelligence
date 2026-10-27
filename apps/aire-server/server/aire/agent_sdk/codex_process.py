"""One `codex exec` invocation — the argv, the image files `-i` takes, the
subprocess and its two pipes. It knows nothing of sessions or mirrors:
`codex.py` owns those and runs one of these per turn."""

from __future__ import annotations

import asyncio
import os
import tempfile
from collections.abc import AsyncIterator
from typing import Any

from .codex_events import IMAGE_EXT

STDERR_TAIL = 2000


class CodexRun:
    def __init__(self, command: tuple[str, ...], cwd: str, model: str, effort: str,
                 allow_tools: bool, prompt: str, images: list[tuple[bytes, str]],
                 thread: str | None, env: dict[str, str] | None = None) -> None:
        self.command, self.cwd, self.model, self.effort = command, cwd, model, effort
        self.allow_tools, self.prompt, self.images, self.thread = allow_tools, prompt, images, thread
        self.env = env or {}
        self._proc: Any = None
        self._stderr: Any = None
        self._tmp: Any = None

    def argv(self, image_paths: list[str]) -> list[str]:
        """`exec` opens a thread, `exec resume <id>` continues one; `-m` rides
        every call (a resume without it falls back to the plan's default weights)
        and the modes dial becomes the sandbox: `agent` may write its casita,
        anything else is read-only. `approval_policy=never` because nobody sits
        at this terminal to answer a prompt."""
        sandbox = "workspace-write" if self.allow_tools else "read-only"
        argv = [*self.command, "exec"]
        if self.thread:
            argv += ["resume", self.thread]
        argv += ["-m", self.model, "-c", f'model_reasoning_effort="{self.effort}"',
                 "-c", f'sandbox_mode="{sandbox}"', "-c", 'approval_policy="never"',
                 "--skip-git-repo-check", "--json"]
        for path in image_paths:
            argv += ["-i", path]
        return [*argv, self.prompt or "(see the attached files)"]

    def _write_images(self) -> list[str]:
        if not self.images:
            return []
        self._tmp = tempfile.TemporaryDirectory(prefix="aire-codex-")
        paths = []
        for i, (raw, media_type) in enumerate(self.images):
            path = os.path.join(self._tmp.name, f"image-{i}{IMAGE_EXT.get(media_type, '.bin')}")
            with open(path, "wb") as fh:
                fh.write(raw)
            paths.append(path)
        return paths

    async def start(self) -> None:
        """The credential slot rides ON TOP of the daemon's environ (#53): the
        process inherits `CODEX_HOME` and gets the slot's own var over it."""
        self._proc = await asyncio.create_subprocess_exec(
            *self.argv(self._write_images()), cwd=self.cwd, stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            env={**os.environ, **self.env})
        self._stderr = asyncio.create_task(self._proc.stderr.read())

    async def lines(self) -> AsyncIterator[bytes]:
        async for line in self._proc.stdout:
            yield line

    async def finish(self) -> tuple[int, str]:
        """The exit code and the stderr tail, once stdout closed."""
        code = await self._proc.wait()
        tail = (await self._stderr)[-STDERR_TAIL:].decode(errors="replace")
        return code, tail

    async def close(self) -> None:
        if self._proc is not None and self._proc.returncode is None:
            self._proc.kill()
            await self._proc.wait()
        if self._tmp is not None:
            self._tmp.cleanup()
            self._tmp = None
