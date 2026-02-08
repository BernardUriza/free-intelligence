"""System routes for health, version, and API discovery.

Extracted from main.py to reduce its size and improve maintainability.
These endpoints are mounted on both the main app and public_app.

Author: Bernard Uriza Orozco
Created: 2026-01-06
"""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import os

# Import version from dedicated module (avoids circular imports)
from backend.app.version import __version__
from fastapi import APIRouter

router = APIRouter(tags=["System"])


# ============================================================================
# Health Endpoints
# ============================================================================


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@router.get("/llm/health")
async def llm_health_check() -> dict:
    """LLM health check endpoint for CI/CD validation.

    Checks if Ollama is available and lists models.
    Used by E2E tests to verify LLM infrastructure.
    """
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                return {
                    "status": "ok",
                    "ollama": True,
                    "models": models,
                    "model_count": len(models),
                }
            return {"status": "degraded", "ollama": False, "models": [], "model_count": 0}
    except Exception as e:
        return {"status": "degraded", "ollama": False, "models": [], "error": str(e)}


# ============================================================================
# Version Endpoints
# ============================================================================


@router.get("/version")
async def version_info() -> dict:
    """Version endpoint for E2E testing.

    Returns version info and sample Python code for validation.
    This endpoint is used by CI/CD to verify successful deployment.
    """
    build_timestamp = datetime.now(UTC).isoformat()

    # Python code that validates the system is working
    python_e2e_code = f'''#!/usr/bin/env python3
"""
AURITY E2E Validation Script
Generated: {build_timestamp}
Version: {__version__}
"""
import requests
import sys

def validate_aurity(base_url: str = "https://app.aurity.io") -> bool:
    """Validate AURITY deployment is working."""
    checks = []

    # 1. Health check
    try:
        r = requests.get(f"{{base_url}}/api/health", timeout=5)
        checks.append(("health", r.status_code == 200))
    except Exception:
        checks.append(("health", False))

    # 2. Version endpoint (this one)
    try:
        r = requests.get(f"{{base_url}}/api/version", timeout=5)
        data = r.json()
        checks.append(("version", data.get("version") == "{__version__}"))
    except Exception:
        checks.append(("version", False))

    # 3. Root endpoint
    try:
        r = requests.get(f"{{base_url}}/api/", timeout=5)
        data = r.json()
        checks.append(("root", data.get("service", {{}}).get("codename") == "AURITY"))
    except Exception:
        checks.append(("root", False))

    # Report
    print(f"AURITY E2E Validation - {{base_url}}")
    print("-" * 40)
    all_pass = True
    for name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"  {{status}} {{name}}")
        if not passed:
            all_pass = False

    print("-" * 40)
    if all_pass:
        print("✅ All checks passed!")
    else:
        print("❌ Some checks failed")

    return all_pass

if __name__ == "__main__":
    base = sys.argv[1] if len(sys.argv) > 1 else "https://app.aurity.io"
    success = validate_aurity(base)
    sys.exit(0 if success else 1)
'''

    return {
        "service": "AURITY",
        "version": __version__,
        "build_timestamp": build_timestamp,
        "environment": os.getenv("ENVIRONMENT", "development"),
        "python_e2e_code": python_e2e_code,
        "usage": {
            "curl": "curl -s https://app.aurity.io/version | jq -r .python_e2e_code | python3",
            "save": "curl -s https://app.aurity.io/version | jq -r .python_e2e_code > validate.py && python3 validate.py",
        },
    }


# ============================================================================
# API Discovery (Root)
# ============================================================================


def get_api_info() -> dict:
    """Generate API discovery information.

    Separated into a function to keep the endpoint handler clean.
    """
    environment = os.getenv("ENVIRONMENT", "development")

    return {
        "service": {
            "name": "Free Intelligence",
            "codename": "AURITY",
            "description": "Advanced Universal Reliable Intelligence for Telemedicine Yield",
            "version": __version__,
            "environment": environment,
            "timestamp": datetime.now(UTC).isoformat(),
        },
        "status": {
            "operational": True,
            "message": "All systems operational",
        },
        "api": {
            "public": {
                "base_url": "/api",
                "description": "Public orchestration endpoints (CORS enabled)",
                "endpoints": {
                    "workflows": "/api/workflows/aurity/*",
                    "sessions": "/api/workflows/aurity/sessions/*",
                    "assistant": "/api/workflows/aurity/assistant/*",
                    "timeline": "/api/sessions/*",
                    "audit": "/api/audit/*",
                    "system": "/api/system/*",
                },
            },
            "internal": {
                "base_url": "/internal",
                "description": "Internal atomic resources (localhost-only in production)",
                "note": "⚠️ Direct access blocked by InternalOnlyMiddleware in production",
                "endpoints": {
                    "audit": "/internal/audit/*",
                    "diarization": "/internal/diarization/*",
                    "exports": "/internal/exports/*",
                    "kpis": "/internal/kpis/*",
                    "sessions": "/internal/sessions/*",
                    "transcribe": "/internal/transcribe/*",
                    "triage": "/internal/triage/*",
                    "llm": "/internal/llm/*",
                },
            },
        },
        "resources": {
            "health": "/health",
            "docs": "/docs",
            "openapi": "/openapi.json",
            "static": "/static",
        },
        "architecture": {
            "pattern": "Layered API (Public Orchestrators + Internal Resources)",
            "philosophy": "LAN-only, append-only HDF5, zero-cloud runtime",
            "security": "RBAC + PolicyEnforcer + InternalOnlyMiddleware",
        },
        "contact": {
            "repository": "https://github.com/BernardUriza/free-intelligence",
            "owner": "Bernard Uriza Orozco",
        },
        "examples": {
            "ai_assistant": {
                "description": "Natural language SOAP modification",
                "method": "POST",
                "endpoint": "/api/workflows/aurity/sessions/{session_id}/assistant",
                "body": {
                    "command": "agrega que el paciente tiene diabetes tipo 2 y es alérgico a penicilina",
                    "current_soap": {
                        "subjective": "Paciente refiere mareos frecuentes",
                        "objective": "PA: 140/90, Glucosa: 180 mg/dl",
                        "assessment": "Hipertensión arterial",
                        "plan": {
                            "medications": ["Metformina 850mg c/12h"],
                            "studies": ["Hemoglobina glucosilada"],
                        },
                    },
                },
                "expected_response": {
                    "updates": {
                        "pastMedicalHistory": "add_item:Diabetes mellitus tipo 2",
                        "allergies": "add_item:Penicilina",
                    },
                    "explanation": "Agregados diabetes tipo 2 y alergia a penicilina",
                    "success": True,
                },
            },
            "get_soap": {
                "description": "Retrieve SOAP note for a session",
                "method": "GET",
                "endpoint": "/api/workflows/aurity/sessions/{session_id}/soap",
                "expected_response": {
                    "session_id": "test_001",
                    "soap_note": {
                        "subjective": "...",
                        "objective": "...",
                        "assessment": "...",
                        "plan": {},
                    },
                },
            },
            "transcribe_audio": {
                "description": "Upload audio chunk for transcription",
                "method": "POST",
                "endpoint": "/api/workflows/aurity/stream",
                "body": "FormData with session_id, chunk_number, and audio file",
                "expected_response": {
                    "status": "accepted",
                    "job_id": "session_id",
                    "message": "Audio chunk received",
                },
            },
        },
        "quick_test": {
            "claude_ai": 'curl -X POST https://api.aurity.io/api/workflows/aurity/sessions/test/assistant -H \'Content-Type: application/json\' -d \'{"command":"test","current_soap":{}}\'',
            "health": "curl https://api.aurity.io/api/health",
            "sessions": "curl https://api.aurity.io/api/workflows/aurity/sessions",
        },
    }


@router.get("/")
async def root() -> dict:
    """Root endpoint - API discovery and system information."""
    return get_api_info()
