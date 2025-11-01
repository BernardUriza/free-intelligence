from __future__ import annotations

"""
Free Intelligence - Main Backend Entrypoint

This module re-exports the LLM middleware FastAPI app for PM2 deployment.

File: backend/main.py
Created: 2025-10-30
Purpose: PM2 entrypoint (ecosystem.config.js → backend.main:app)

Port: 9001
Endpoints: /llm/generate, /llm/prompt, /health, /metrics

Usage:
  uvicorn backend.main:app --host 0.0.0.0 --port 9001 --workers 2
"""

from backend.llm_middleware import app

__all__ = ["app"]
