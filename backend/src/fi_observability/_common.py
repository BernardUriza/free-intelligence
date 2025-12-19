from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_ENV_CHOICES: tuple[str, ...] = ("local", "staging", "production")


SENSITIVE_KEY_RE = re.compile(
    r"(?ix)"
    r"(^|_)"
    r"("
    r"name|nombre|apellido|email|mail|phone|telefono|tel|mobile|"
    r"address|direccion|street|zip|postal|dob|birth|fecha_nacimiento|"
    r"curp|ssn|nss|passport|"
    r"transcript|transcription|note|notes|message|content|text|body|audio|"
    r"authorization|cookie|set-cookie|token|api[_-]?key|secret|password|jwt"
    r")"
    r"($|_)"
)


@dataclass(frozen=True)
class CommonArgs:
    base_path: str
    log_source: str | None
    slo_policy: str
    environment: str
    out_dir: str


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--base-path",
        required=True,
        help=(
            "Absolute path to the repository root or backend folder that contains fi_devtools. "
            "Used for validation only (read-only)."
        ),
    )
    parser.add_argument(
        "--log-source",
        default=None,
        help=(
            "Structured JSON logs source (JSONL). Use a file path for append-only logs or '-' for stdin. "
            "Some tools don't require it."
        ),
    )
    parser.add_argument(
        "--slo-policy",
        required=True,
        help="Path to active SLO policy (YAML or JSON).",
    )
    parser.add_argument(
        "--environment",
        required=True,
        choices=_ENV_CHOICES,
        help="Execution environment label.",
    )
    parser.add_argument(
        "--out-dir",
        default="artifacts/fi_observability",
        help="Output directory for verifiable artifacts.",
    )


def validate_base_path(base_path: str) -> Path:
    """Validate that fi_devtools exists under the given base path.

    Accepts either repo root (contains backend/) or backend root (contains src/).
    """

    base = Path(base_path).expanduser().resolve()
    if not base.exists():
        raise ValueError(f"base_path does not exist: {base}")

    candidates = [
        base / "src" / "fi_devtools",
        base / "backend" / "src" / "fi_devtools",
    ]

    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return base

    raise ValueError(
        "base_path does not appear to contain fi_devtools. "
        "Expected to find 'src/fi_devtools' (backend root) or 'backend/src/fi_devtools' (repo root)."
    )


def _try_load_yaml(text: str) -> Any:
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text)
    except Exception:
        return None


def load_policy(path: str) -> dict[str, Any]:
    policy_path = Path(path).expanduser().resolve()
    raw = policy_path.read_text(encoding="utf-8")

    if policy_path.suffix.lower() in {".json"}:
        data = json.loads(raw)
    elif policy_path.suffix.lower() in {".yaml", ".yml"}:
        parsed = _try_load_yaml(raw)
        if parsed is None:
            raise ValueError(
                "YAML SLO policy provided but PyYAML is not available. "
                "Use JSON or install PyYAML in your environment."
            )
        data = parsed
    else:
        # Best-effort: try JSON then YAML.
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            parsed = _try_load_yaml(raw)
            if parsed is None:
                raise
            data = parsed

    if not isinstance(data, dict):
        raise ValueError("SLO policy must be a mapping (top-level object)")

    return data


def policy_sha256(policy: Mapping[str, Any]) -> str:
    b = json.dumps(policy, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(b).hexdigest()


def parse_time(value: Any) -> datetime | None:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        # unix seconds
        try:
            return datetime.fromtimestamp(float(value), tz=UTC)
        except Exception:
            return None

    if isinstance(value, str):
        v = value.strip()
        if not v:
            return None

        # unix millis/seconds as string
        if re.fullmatch(r"\d{10}(?:\.\d+)?", v):
            try:
                return datetime.fromtimestamp(float(v), tz=UTC)
            except Exception:
                return None
        if re.fullmatch(r"\d{13}", v):
            try:
                return datetime.fromtimestamp(float(v) / 1000.0, tz=UTC)
            except Exception:
                return None

        # ISO 8601 (allow trailing Z)
        try:
            if v.endswith("Z"):
                v = v[:-1] + "+00:00"
            dt = datetime.fromisoformat(v)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=UTC)
            return dt.astimezone(UTC)
        except Exception:
            return None

    return None


def parse_duration_ms(event: Mapping[str, Any]) -> float | None:
    candidates: list[tuple[str, float]] = []

    def _num(x: Any) -> float | None:
        if isinstance(x, (int, float)):
            return float(x)
        if isinstance(x, str):
            try:
                return float(x)
            except Exception:
                return None
        return None

    # Most common keys
    for key in ("latency_ms", "duration_ms", "elapsed_ms", "request_latency_ms"):
        n = _num(event.get(key))
        if n is not None:
            candidates.append((key, n))

    # Seconds keys (convert)
    for key in ("latency_s", "duration_s", "elapsed_s"):
        n = _num(event.get(key))
        if n is not None:
            candidates.append((key, n * 1000.0))

    # Generic fallback
    n = _num(event.get("duration"))
    if n is not None:
        # Heuristic: treat <= 30 as seconds, else ms
        candidates.append(("duration", n * 1000.0 if n <= 30.0 else n))

    if not candidates:
        return None

    # Prefer explicit *_ms keys
    candidates.sort(key=lambda kv: (0 if kv[0].endswith("_ms") else 1, kv[0]))
    return candidates[0][1]


def get_endpoint(event: Mapping[str, Any]) -> str | None:
    for key in ("endpoint", "path", "route", "request_path", "http_path"):
        v = event.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()

    # structlog sometimes uses event="..." but we must not treat it as an endpoint.
    return None


def get_layer(event: Mapping[str, Any]) -> str | None:
    v = event.get("layer") or event.get("service_layer") or event.get("tier")
    if isinstance(v, str) and v.strip():
        up = v.strip().upper()
        if up in {"PUBLIC", "INTERNAL", "WORKER"}:
            return up
        return v.strip()
    return None


def get_status_code(event: Mapping[str, Any]) -> int | None:
    for key in ("status_code", "http_status", "status"):
        v = event.get(key)
        if isinstance(v, int):
            return v
        if isinstance(v, str) and v.isdigit():
            return int(v)
    return None


def iter_json_logs(log_source: str) -> Iterator[dict[str, Any]]:
    if log_source == "-":
        stream: io.TextIOBase = sys.stdin
        yield from _iter_jsonl_stream(stream)
        return

    path = Path(log_source).expanduser().resolve()
    with path.open("r", encoding="utf-8") as f:
        yield from _iter_jsonl_stream(f)


def _iter_jsonl_stream(stream: io.TextIOBase) -> Iterator[dict[str, Any]]:
    for line in stream:
        s = line.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            # Ignore malformed lines deterministically.
            continue
        if isinstance(obj, dict):
            yield obj


def redact_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return redact_mapping(value)
    if isinstance(value, list):
        return [redact_value(v) for v in value]
    if isinstance(value, tuple):
        return tuple(redact_value(v) for v in value)
    return value


def redact_mapping(obj: Mapping[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in obj.items():
        if not isinstance(key, str):
            redacted[str(key)] = redact_value(value)
            continue

        if SENSITIVE_KEY_RE.search(key):
            redacted[key] = "[REDACTED]"
        else:
            redacted[key] = redact_value(value)
    return redacted


def write_json_artifact(out_dir: str, filename: str, payload: Mapping[str, Any]) -> Path:
    out_path = Path(out_dir).expanduser().resolve()
    out_path.mkdir(parents=True, exist_ok=True)

    target = out_path / filename
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    target.write_bytes(encoded)

    sha = hashlib.sha256(encoded).hexdigest()
    (out_path / f"{filename}.sha256").write_text(f"{sha}  {filename}\n", encoding="utf-8")
    return target


def write_text_artifact(out_dir: str, filename: str, text: str) -> Path:
    out_path = Path(out_dir).expanduser().resolve()
    out_path.mkdir(parents=True, exist_ok=True)

    target = out_path / filename
    encoded = text.encode("utf-8")
    target.write_bytes(encoded)

    sha = hashlib.sha256(encoded).hexdigest()
    (out_path / f"{filename}.sha256").write_text(f"{sha}  {filename}\n", encoding="utf-8")
    return target


def percentile(values: Sequence[float], q: float) -> float | None:
    if not values:
        return None

    if q <= 0:
        return float(min(values))
    if q >= 1:
        return float(max(values))

    xs = sorted(values)
    # Nearest-rank method (deterministic)
    k = round(q * (len(xs) - 1))
    k = max(0, min(len(xs) - 1, k))
    return float(xs[k])


def coerce_common_args(ns: argparse.Namespace) -> CommonArgs:
    return CommonArgs(
        base_path=str(ns.base_path),
        log_source=(str(ns.log_source) if ns.log_source is not None else None),
        slo_policy=str(ns.slo_policy),
        environment=str(ns.environment),
        out_dir=str(ns.out_dir),
    )


def safe_print(obj: Mapping[str, Any]) -> None:
    # Avoid accidental PHI/PII in stdout: redact before printing.
    red = redact_mapping(obj)
    sys.stdout.write(json.dumps(red, sort_keys=True, ensure_ascii=False) + "\n")


def within_range(ts: datetime | None, since: datetime | None, until: datetime | None) -> bool:
    if ts is None:
        return False
    if since is not None and ts < since:
        return False
    return not (until is not None and ts > until)


def best_effort_timestamp(event: Mapping[str, Any]) -> datetime | None:
    for key in ("timestamp", "ts", "time", "event_time", "created_at"):
        ts = parse_time(event.get(key))
        if ts is not None:
            return ts
    return None


def normalize_service(event: Mapping[str, Any], endpoint: str | None) -> str:
    service = event.get("service")
    if isinstance(service, str) and service.strip():
        return service.strip().lower()

    layer = get_layer(event)
    if layer == "PUBLIC":
        return "public_api"
    if layer == "INTERNAL":
        return "internal"
    if layer == "WORKER":
        return "worker"

    if endpoint and "realtime" in endpoint.lower():
        return "realtime_talk"
    if endpoint and "soap" in endpoint.lower():
        return "soap_generation"

    return "unknown"


def slo_limits(policy: Mapping[str, Any], service: str) -> dict[str, float]:
    # Flexible schema:
    # - {services: {public_api: {p95_ms: 800, error_rate: 0.01}}}
    # - {public_api: {p95_ms: 800, error_rate: 0.01}}
    services = policy.get("services") if isinstance(policy.get("services"), Mapping) else policy
    if not isinstance(services, Mapping):
        return {}

    entry = services.get(service)
    if not isinstance(entry, Mapping):
        return {}

    limits: dict[str, float] = {}
    for k in ("p95_ms", "p99_ms", "p50_ms"):
        v = entry.get(k)
        if isinstance(v, (int, float)):
            limits[k] = float(v)
    er = entry.get("error_rate")
    if isinstance(er, (int, float)):
        limits["error_rate"] = float(er)

    return limits


def build_parser(prog: str, description: str) -> argparse.ArgumentParser:
    return argparse.ArgumentParser(prog=prog, description=description)


def require_log_source(common: CommonArgs) -> str:
    if common.log_source is None:
        raise ValueError("--log-source is required for this tool")
    return common.log_source


def traceability_block(prompt_id: str) -> dict[str, str]:
    return {
        "aurity_prompt_id": prompt_id,
        "date": "2025-12-18",
        "version": "1.0",
    }


def ensure_read_only_mode(explicit_flag: bool = True) -> None:
    # Guardrail: these tools do not mutate disk/network state beyond GET probes and writing artifacts.
    # This is intentionally minimal and deterministic.
    if not explicit_flag:
        raise ValueError("read-only mode must be enabled")


def compact_exception(e: Exception) -> dict[str, Any]:
    return {
        "error": e.__class__.__name__,
        "message": str(e)[:500],
    }
