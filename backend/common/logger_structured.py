#!/usr/bin/env python3
from __future__ import annotations

"""
Free Intelligence - Structured Logging System

Sistema de logging estructurado NDJSON con rotación, retención y manifest encadenado.
Implementa 4 canales: server, llm, storage, access (AUDIT).

FI-CORE-FEAT-003
"""

import hashlib
import json
import socket
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional


class LogLevel(str, Enum):
    """Log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    AUDIT = "AUDIT"


class ServiceChannel(str, Enum):
    """Service channels for logging."""

    SERVER = "server"
    LLM = "llm"
    STORAGE = "storage"
    ACCESS = "access"


class UserRole(str, Enum):
    """User roles for RBAC."""

    OWNER = "owner"
    ADMIN = "admin"
    ANALYST = "analyst"
    GUEST = "guest"
    SYSTEM = "system"


@dataclass
class BaseLogEvent:
    """
    Base log event structure.

    Todos los eventos deben tener estos campos obligatorios:
    - ts: ISO 8601 con timezone
    - host: hostname
    - service: canal (server|llm|storage|access)
    - version: versión FI
    - level: DEBUG|INFO|WARN|ERROR|AUDIT
    - trace_id: UUID v4 para trazabilidad
    - span_id: UUID v4 para spans
    - session_id: UUID v4 para sesión
    - user: hash estable o 'system'
    - role: owner|admin|analyst|guest|system
    - action: descriptor de acción (ej. api.request)
    - ok: bool de éxito/fallo
    - latency_ms: latencia en milisegundos (opcional)
    - ref: ID en HDF5/DB (opcional)
    - pii: bool indicando si contiene PII (siempre false en MVP)
    - details: dict con detalles específicos del canal
    """

    # Required fields
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    host: str = field(default_factory=lambda: socket.gethostname())
    service: ServiceChannel = field(default=ServiceChannel.SERVER)  # type: ignore[assignment]
    version: str = "0.3.0"
    level: LogLevel = field(default=LogLevel.INFO)  # type: ignore[assignment]
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    span_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str | None = None
    user: str = "system"
    role: UserRole = field(default=UserRole.SYSTEM)  # type: ignore[assignment]
    action: str = "unknown"
    ok: bool = True
    latency_ms: float | None = None
    ref: str | None = None
    pii: bool = False  # Siempre false en MVP
    details: dict[str, Any] = field(default_factory=dict)

    def to_ndjson(self) -> str:
        """Convert to NDJSON line (single-line JSON)."""
        return json.dumps(asdict(self), ensure_ascii=False)

    def compute_hash(self) -> str:
        """Compute SHA256 hash of event for manifest."""
        return hashlib.sha256(self.to_ndjson().encode()).hexdigest()


def hash_user_id(user_id: str, salt: str = "fi-salt-2025") -> str:
    """
    Hash user ID para privacidad.

    Args:
        user_id: User identifier
        salt: Salt para hashing

    Returns:
        SHA256 hash (primeros 16 caracteres)
    """
    if user_id == "system":
        return "system"

    hash_full = hashlib.sha256(f"{user_id}{salt}".encode()).hexdigest()
    return hash_full[:16]


def hash_prompt(prompt: str) -> str:
    """
    Hash de prompt para trazabilidad sin exponer contenido.

    Args:
        prompt: Texto del prompt

    Returns:
        SHA256 hash completo
    """
    return hashlib.sha256(prompt.encode()).hexdigest()


def anonymize_ip(ip: str, subnet_mask: int = 24) -> str:
    """
    Anonimizar IP address a nivel de subnet.

    Args:
        ip: IP address (x.y.z.w)
        subnet_mask: Bits de subnet (24 para /24)

    Returns:
        IP anonimizada (ej. x.y.z.0/24)
    """
    if ip in ["127.0.0.1", "localhost", "::1"]:
        return ip

    parts = ip.split(".")
    if len(parts) == 4 and subnet_mask == 24:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"

    return ip


def truncate_preview(text: str, max_length: int = 120, sensitive: bool = False) -> Optional[str]:
    """
    Truncar texto para preview sin exponer datos sensibles.

    Args:
        text: Texto original
        max_length: Longitud máxima
        sensitive: Si es true, retorna None (no guardar preview)

    Returns:
        Texto truncado o None si sensitive=true
    """
    if sensitive:
        return None

    if len(text) <= max_length:
        return text

    return text[:max_length] + "..."


# ============================================================================
# Channel-specific log events
# ============================================================================


def log_server_request(
    method: str,
    path: str,
    status: int,
    bytes_sent: int,
    client_ip: str,
    latency_ms: float,
    trace_id: str | None = None,
    session_id: str | None = None,
    user: str = "system",
    role: UserRole | None = None,
) -> BaseLogEvent:
    """
    Log server API request.

    Canal: server
    Contenido: método, ruta, status, bytes, client_ip (anonimizada), sin body
    """
    return BaseLogEvent(  # type: ignore[call-arg]
        service=ServiceChannel.SERVER,
        level=LogLevel.INFO if status < 400 else LogLevel.ERROR,
        trace_id=trace_id or str(uuid.uuid4()),
        session_id=session_id,
        user=hash_user_id(user),
        role=role or UserRole.SYSTEM,
        action="api.request",
        ok=status < 400,
        latency_ms=latency_ms,
        details={
            "method": method,
            "path": path,
            "status": status,
            "bytes_sent": bytes_sent,
            "client_ip": anonymize_ip(client_ip),
        },
    )


def log_llm_request(
    provider: str,
    model: str,
    tokens_in: int,
    tokens_out: int,
    cost_est: float,
    prompt: str,
    response: str,
    latency_ms: float,
    sensitive: bool = False,
    timeout: bool = False,
    retry_count: int = 0,
    trace_id: str | None = None,
    session_id: str | None = None,
    user: str = "system",
    role: UserRole | None = None,
) -> BaseLogEvent:
    """
    Log LLM API request.

    Canal: llm
    Contenido: provider, model, tokens, cost, prompt_hash, response_preview (≤120 chars)
    Si sensitive=true, no guarda preview.
    """
    prompt_hash_val = hash_prompt(prompt)
    response_preview = truncate_preview(response, max_length=120, sensitive=sensitive)

    return BaseLogEvent(  # type: ignore[call-arg]
        service=ServiceChannel.LLM,
        level=LogLevel.WARN if timeout else LogLevel.INFO,
        trace_id=trace_id or str(uuid.uuid4()),
        session_id=session_id,
        user=hash_user_id(user),
        role=role or UserRole.SYSTEM,
        action="llm.request",
        ok=not timeout,
        latency_ms=latency_ms,
        details={
            "provider": provider,
            "model": model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_est": cost_est,
            "prompt_hash": prompt_hash_val,
            "response_preview": response_preview,
            "timeout": timeout,
            "retry_count": retry_count,
        },
    )


def log_storage_segment(
    file_path: str,
    sha256: str,
    segment_seconds: float,
    ready: bool,
    trace_id: Optional[str] = None,
    session_id: Optional[str] = None,
    user: str = "system",
) -> BaseLogEvent:
    """
    Log storage segmentation event.

    Canal: storage
    Contenido: file, sha256, segment_seconds, ready=true/false
    """
    return BaseLogEvent(  # type: ignore[call-arg]
        service=ServiceChannel.STORAGE,
        level=LogLevel.INFO,
        trace_id=trace_id or str(uuid.uuid4()),
        session_id=session_id,
        user=hash_user_id(user),
        role=UserRole.SYSTEM,
        action="storage.segmented",
        ok=ready,
        ref=sha256,
        details={
            "file": file_path,
            "sha256": sha256,
            "segment_seconds": segment_seconds,
            "ready": ready,
        },
    )


def log_access_event(
    action: Literal["login", "logout", "role_change", "policy_update"],
    client_ip: str,
    result: bool,
    user: str,
    old_role: UserRole | None = None,
    new_role: UserRole | None = None,
    trace_id: str | None = None,
    session_id: str | None = None,
    details: Optional[dict[str, Any | None]] = None,
) -> BaseLogEvent:
    """
    Log access event (AUDIT).

    Canal: access
    Contenido: login|logout|role_change|policy_update, ip, result
    Nivel: AUDIT (retención 180 días, WORM lógico)
    """
    action_name = f"access.{action}"

    event_details: dict[str, Any] = {
        "client_ip": anonymize_ip(client_ip),
        "result": "success" if result else "failed",
    }

    if action == "role_change" and old_role and new_role:
        event_details["old_role"] = old_role.value
        event_details["new_role"] = new_role.value

    if details:
        event_details.update(details)  # type: ignore[arg-type]

    return BaseLogEvent(  # type: ignore[call-arg]
        service=ServiceChannel.ACCESS,
        level=LogLevel.AUDIT,
        trace_id=trace_id or str(uuid.uuid4()),
        session_id=session_id,
        user=hash_user_id(user),
        role=new_role or UserRole.GUEST,
        action=action_name,
        ok=result,
        details=event_details,
    )


# ============================================================================
# CLI Demo
# ============================================================================

if __name__ == "__main__":
    print("🔍 FREE INTELLIGENCE - STRUCTURED LOGGING DEMO")
    print("=" * 60)
    print()

    # Demo 1: Server request
    print("1️⃣  Server Request Log")
    server_event = log_server_request(
        method="POST",
        path="/api/consultations",
        status=201,
        bytes_sent=1024,
        client_ip="192.168.1.100",
        latency_ms=45.3,
        user="bernard@example.com",
        role=UserRole.OWNER,
    )
    print(f"   {server_event.to_ndjson()}")
    print()

    # Demo 2: LLM request
    print("2️⃣  LLM Request Log")
    llm_event = log_llm_request(
        provider="anthropic",
        model="claude-3-5-sonnet-20241022",
        tokens_in=100,
        tokens_out=250,
        cost_est=0.0015,
        prompt="What are the symptoms of chest pain?",
        response="Chest pain can indicate various conditions ranging from minor to life-threatening...",
        latency_ms=1234.5,
        sensitive=False,
        user="bernard@example.com",
        role=UserRole.OWNER,
    )
    print(f"   {llm_event.to_ndjson()[:200]}...")
    print()

    # Demo 3: Storage segment
    print("3️⃣  Storage Segment Log")
    storage_event = log_storage_segment(
        file_path="storage/corpus.h5", sha256="abc123def456...", segment_seconds=0.045, ready=True
    )
    print(f"   {storage_event.to_ndjson()}")
    print()

    # Demo 4: Access event (AUDIT)
    print("4️⃣  Access Event Log (AUDIT)")
    access_event = log_access_event(
        action="login", client_ip="192.168.1.100", result=True, user="bernard@example.com"
    )
    print(f"   {access_event.to_ndjson()}")
    print()

    # Demo 5: Sensitive LLM (no preview)
    print("5️⃣  Sensitive LLM Request (no preview)")
    sensitive_llm = log_llm_request(
        provider="anthropic",
        model="claude-3-5-sonnet-20241022",
        tokens_in=50,
        tokens_out=100,
        cost_est=0.0008,
        prompt="Patient's SSN is 123-45-6789",
        response="I cannot process SSN data",
        latency_ms=500.0,
        sensitive=True,  # No guarda preview
        user="system",
    )
    print(f"   response_preview: {sensitive_llm.details.get('response_preview')}")
    print("   (Expected: None)")
    print()

    print("✅ Demo complete!")
    print()
    print("Event hashes (for manifest):")
    print(f"   Server: {server_event.compute_hash()[:16]}...")
    print(f"   LLM: {llm_event.compute_hash()[:16]}...")
    print(f"   Storage: {storage_event.compute_hash()[:16]}...")
    print(f"   Access: {access_event.compute_hash()[:16]}...")
