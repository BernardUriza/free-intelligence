"""FI Backend - Organized by responsibility domains.

Modules:
  - app/           : FastAPI application, middlewares, entry points
  - api/           : REST API route handlers
  - services/      : Business logic and domain services
  - jobs/          : Background workers and async jobs
  - storage/       : Data layer (HDF5, audio, sessions)
  - providers/     : LLM adapters and external integrations
  - policy/        : Access control, validation, enforcement
  - schemas/       : Data models, validators, event definitions
  - common/        : Shared utilities (logger, config, cache, etc)
  - security/      : Security utilities (IP validation, etc)
  - repositories/  : Data access patterns
  - cli/           : Command-line tools
  - tools/         : Utility scripts and helpers
"""

from __future__ import annotations
