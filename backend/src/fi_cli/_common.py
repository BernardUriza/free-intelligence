from __future__ import annotations

import re
import shlex
import subprocess
import time
from dataclasses import dataclass
from enum import IntEnum

import os
import typer
from pathlib import Path


class ExitCode(IntEnum):
    OK = 0
    WARNING = 10
    ERROR = 20
    USAGE = 64


@dataclass(frozen=True)
class ProjectPaths:
    repo_root: Path
    backend_root: Path
    frontend_root: Path
    logs_dir: Path
    storage_dir: Path


DEFAULT_ENVIRONMENTS: set[str] = {"local", "staging", "production"}


def resolve_repo_root(base_path: Path | None) -> Path:
    """Resolve repo root from --base-path (repo root or backend/)."""
    if base_path is None:
        cwd = Path.cwd().resolve()
        for candidate in [cwd, *cwd.parents]:
            if (candidate / "backend").exists() and (candidate / "apps").exists():
                return candidate
        raise typer.BadParameter("Could not infer repo root; pass --base-path")

    base_path = base_path.expanduser().resolve()
    repo_root = base_path.parent if base_path.name == "backend" else base_path

    if not (repo_root / "backend").exists():
        raise typer.BadParameter(f"backend/ not found under: {repo_root}")
    if not (repo_root / "apps").exists():
        raise typer.BadParameter(f"apps/ not found under: {repo_root}")
    return repo_root


def build_paths(repo_root: Path) -> ProjectPaths:
    return ProjectPaths(
        repo_root=repo_root,
        backend_root=repo_root / "backend",
        frontend_root=repo_root / "apps" / "aurity",
        logs_dir=repo_root / "logs",
        storage_dir=repo_root / "storage",
    )


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def run_cmd(
    argv: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    check: bool = True,
    capture_output: bool = False,
    text: bool = True,
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    try:
        proc = subprocess.run(
            argv,
            cwd=str(cwd) if cwd else None,
            env=merged_env,
            check=check,
            capture_output=capture_output,
            text=text,
        )
    except FileNotFoundError as exc:
        typer.echo(f"❌ Command not found: {argv[0]}", err=True)
        raise typer.Exit(code=int(ExitCode.ERROR)) from exc
    except subprocess.CalledProcessError as exc:
        if capture_output and exc.stdout:
            typer.echo(exc.stdout)
        if capture_output and exc.stderr:
            typer.echo(exc.stderr, err=True)
        raise typer.Exit(code=int(ExitCode.ERROR)) from exc

    return proc


def popen_cmd(
    argv: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    stdout_path: Path | None = None,
) -> subprocess.Popen[bytes]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    stdout = None
    if stdout_path is not None:
        ensure_dir(stdout_path.parent)
        stdout = stdout_path.open("ab")

    try:
        return subprocess.Popen(
            argv,
            cwd=str(cwd) if cwd else None,
            env=merged_env,
            stdout=stdout,
            stderr=subprocess.STDOUT if stdout is not None else None,
        )
    except FileNotFoundError as exc:
        typer.echo(f"❌ Command not found: {argv[0]}", err=True)
        raise typer.Exit(code=int(ExitCode.ERROR)) from exc


def shell_cmd(command: str, *, cwd: Path | None = None, check: bool = True) -> None:
    run_cmd(["bash", "-lc", command], cwd=cwd, check=check)


def wait_for_http_ok(url: str, *, timeout_s: int, interval_s: float = 1.0) -> bool:
    import urllib.error
    import urllib.request

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                if 200 <= resp.status < 300:
                    return True
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(interval_s)
    return False


def format_argv(argv: list[str]) -> str:
    return " ".join(shlex.quote(a) for a in argv)


def require_env_choice(environment: str, allowed: set[str] | None = None) -> str:
    allowed = DEFAULT_ENVIRONMENTS if allowed is None else allowed
    if environment not in allowed:
        raise typer.BadParameter(f"Invalid environment: {environment}. Allowed: {sorted(allowed)}")
    return environment


_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_TOKEN_RE = re.compile(r"\b(bearer\s+)?[A-Za-z0-9_\-]{24,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"\b(\+?\d[\d\s\-()]{7,}\d)\b")
_CURP_RE = re.compile(r"\b[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d\b")


def redact_text(text: str) -> str:
    """Best-effort redaction for CLI output (no PHI/PII)."""
    text = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    text = _CURP_RE.sub("[REDACTED_CURP]", text)
    text = _PHONE_RE.sub("[REDACTED_PHONE]", text)
    text = _TOKEN_RE.sub("[REDACTED_TOKEN]", text)
    return text


def ssh_argv(
    *,
    host: str,
    user: str | None,
    port: int | None,
    identity_file: Path | None,
    remote_command: str,
) -> list[str]:
    """Build ssh argv for remote command execution (key-based; no passwords)."""
    target = f"{user}@{host}" if user else host
    argv: list[str] = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=30",
    ]
    if port is not None:
        argv += ["-p", str(port)]
    if identity_file is not None:
        argv += ["-i", str(identity_file)]
    argv.append(target)
    argv.append(remote_command)
    return argv
