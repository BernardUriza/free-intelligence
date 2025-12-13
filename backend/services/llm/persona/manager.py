"""
PersonaManager - Free Intelligence v2.0

Main persona management class that orchestrates all persona operations.

ARCHITECTURE (Template → Override Pattern):
- Templates: /backend/config/personas/*.yaml (immutable base, version-controlled)
- Overrides: runtime > user > org > template (merge order)
- Validation: Pydantic v2 with strict schema
- Cache: SHA256 + mtime + TTL for hot-reload

Conformidad: C3-AURITY-2025 · Zero-trust prompts
Aurity-Prompt-ID: AUR-PERSONA-MANAGER-2.0
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import TYPE_CHECKING

import structlog
import yaml

from .config import CacheEntry, PersonaConfig
from .constants import DEFAULT_CACHE_TTL_S, DEFAULT_MAX_RAG_CHARS
from .exceptions import PersonaNotFound
from .prompt_builder import PromptBuilder
from .router import PersonaRouter
from .schemas import PersonaTemplateModel

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = structlog.get_logger(__name__)


class PersonaManager:
    """Gestor de personas de Free-Intelligence (v2.0).

    Features:
    - Pydantic validation of YAML templates
    - SHA256 + mtime cache with TTL hot-reload
    - Multi-level override merge (runtime > user > org > template)
    - Secure prompt building with markers and RAG limits
    - Structured logging with structlog

    Usage:
        manager = PersonaManager()
        config = manager.get_persona("general_assistant")
        prompt = manager.build_system_prompt("general_assistant", context={...})
    """

    def __init__(
        self,
        config_dir: Path | None = None,
        cache_ttl_s: int = DEFAULT_CACHE_TTL_S,
        max_rag_chars: int = DEFAULT_MAX_RAG_CHARS,
    ) -> None:
        """Initialize persona manager.

        Args:
            config_dir: Directory containing persona YAML files
            cache_ttl_s: Cache TTL in seconds for hot-reload
            max_rag_chars: Maximum characters for RAG context
        """
        self._config_dir = config_dir or (
            Path(__file__).parent.parent.parent.parent / "config" / "personas"
        )
        self._cache_ttl_s = cache_ttl_s
        self._cache: dict[str, CacheEntry] = {}

        # Initialize subcomponents
        self._prompt_builder = PromptBuilder(max_rag_chars=max_rag_chars)
        self._router = PersonaRouter()

        self._load_all_personas()

    # ========================================================================
    # LOADING & CACHING
    # ========================================================================

    def _compute_sha256(self, content: bytes) -> str:
        """Compute SHA256 hash of content (truncated to 16 chars)."""
        return hashlib.sha256(content).hexdigest()[:16]

    def _load_persona_from_file(self, yaml_path: Path) -> PersonaConfig | None:
        """Load and validate a single persona from YAML file.

        Returns None if validation fails (logs warning).
        """
        try:
            content = yaml_path.read_bytes()
            sha256 = self._compute_sha256(content)
            mtime = yaml_path.stat().st_mtime

            data = yaml.safe_load(content.decode("utf-8"))
            if not data:
                logger.warning("PERSONA_YAML_EMPTY", path=str(yaml_path))
                return None

            # Validate with Pydantic
            validated = PersonaTemplateModel(**data)

            config = PersonaConfig(
                persona=validated.persona,
                system_prompt=validated.system_prompt,
                model=validated.model or "qwen3:1.7b",
                temperature=validated.temperature,
                max_tokens=validated.max_tokens,
                description=validated.description,
                voice=validated.voice,
                template_sha256=sha256,
                template_version=validated.version,
            )

            # Update cache
            self._cache[validated.persona] = CacheEntry(
                config=config,
                sha256=sha256,
                mtime=mtime,
                loaded_at=time.time(),
            )

            logger.debug(
                "PERSONA_LOADED",
                persona=validated.persona,
                sha256=sha256,
                version=validated.version,
                path=str(yaml_path),
            )

            return config

        except Exception as e:
            logger.warning(
                "PERSONA_LOAD_FAILED",
                path=str(yaml_path),
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    def _load_all_personas(self) -> None:
        """Load all personas from YAML files."""
        if not self._config_dir.exists():
            logger.error("PERSONA_DIR_NOT_FOUND", path=str(self._config_dir))
            raise FileNotFoundError(f"Personas config directory not found: {self._config_dir}")

        loaded = 0
        failed = 0

        for yaml_file in self._config_dir.glob("*.yaml"):
            result = self._load_persona_from_file(yaml_file)
            if result:
                loaded += 1
            else:
                failed += 1

        logger.info(
            "PERSONAS_INITIALIZED",
            loaded=loaded,
            failed=failed,
            cache_ttl_s=self._cache_ttl_s,
        )

    def _check_and_reload_if_stale(self, persona: str) -> None:
        """Check if cached persona is stale and reload if needed."""
        if persona not in self._cache:
            return

        entry = self._cache[persona]
        now = time.time()

        # Check TTL
        if now - entry.loaded_at < self._cache_ttl_s:
            logger.debug("CACHE_HIT", persona=persona)
            return

        # Check mtime
        yaml_path = self._config_dir / f"{persona}.yaml"
        if not yaml_path.exists():
            logger.debug("CACHE_STALE_NO_FILE", persona=persona)
            return

        current_mtime = yaml_path.stat().st_mtime
        if current_mtime == entry.mtime:
            # Update loaded_at to extend TTL
            self._cache[persona] = CacheEntry(
                config=entry.config,
                sha256=entry.sha256,
                mtime=entry.mtime,
                loaded_at=now,
            )
            logger.debug("CACHE_REFRESH", persona=persona)
            return

        # mtime changed - reload
        logger.info(
            "CACHE_STALE_RELOAD",
            persona=persona,
            old_mtime=entry.mtime,
            new_mtime=current_mtime,
        )
        self._load_persona_from_file(yaml_path)

    # ========================================================================
    # PUBLIC API
    # ========================================================================

    def get_persona(self, persona: str) -> PersonaConfig:
        """Get persona configuration (with cache check).

        Args:
            persona: Persona identifier

        Returns:
            PersonaConfig

        Raises:
            PersonaNotFound: If persona doesn't exist
        """
        self._check_and_reload_if_stale(persona)

        if persona not in self._cache:
            raise PersonaNotFound(persona, list(self._cache.keys()))

        return self._cache[persona].config

    def list_personas(self) -> list[str]:
        """List all available personas (sorted alphabetically)."""
        return sorted(self._cache.keys())

    def get_persona_description(self, persona: str) -> str:
        """Get persona description."""
        return self.get_persona(persona).description

    # ========================================================================
    # PROMPT BUILDING (delegated to PromptBuilder)
    # ========================================================================

    def build_system_prompt(
        self,
        persona: str,
        context: dict | None = None,
    ) -> str:
        """Build system prompt with secure RAG injection and mode markers.

        Args:
            persona: Persona identifier
            context: Context dict with response_mode, rag_context, etc.

        Returns:
            Complete system prompt
        """
        config = self.get_persona(persona)
        return self._prompt_builder.build(config, context)

    # ========================================================================
    # ROUTING (delegated to PersonaRouter)
    # ========================================================================

    def route_persona(self, user_message: str) -> str:
        """Route user message to appropriate persona.

        Args:
            user_message: User's input message

        Returns:
            Persona identifier
        """
        return self._router.route(user_message)

    # ========================================================================
    # MULTI-LEVEL OVERRIDE MERGE
    # ========================================================================

    def get_effective_persona(
        self,
        persona: str,
        user_id: str | None = None,
        org_id: str | None = None,
        runtime_overrides: dict | None = None,
        db: Session | None = None,
    ) -> PersonaConfig:
        """Get persona with multi-level overrides merged.

        Merge order (highest precedence first):
        1. runtime_overrides (passed at call time)
        2. user overrides (from DB)
        3. org overrides (from DB) - future
        4. template (YAML)

        Args:
            persona: Persona identifier
            user_id: User UUID for user-level overrides
            org_id: Organization ID for org-level overrides (future)
            runtime_overrides: Dict with runtime overrides
            db: SQLAlchemy session for DB queries

        Returns:
            PersonaConfig with all overrides applied
        """
        # Start with template
        template = self.get_persona(persona)

        # Collect override values
        model = template.model
        system_prompt = template.system_prompt
        temperature = template.temperature
        max_tokens = template.max_tokens
        voice = template.voice

        # Layer 1: User overrides from DB
        if user_id and db:
            try:
                from backend.models.db_models import UserPersonaConfig

                user_override = (
                    db.query(UserPersonaConfig)
                    .filter_by(user_id=user_id, persona_id=persona)
                    .first()
                )

                if user_override:
                    if user_override.model:
                        model = user_override.model
                    if user_override.custom_prompt:
                        system_prompt = user_override.custom_prompt
                    if user_override.temperature is not None:
                        temperature = user_override.temperature
                    if user_override.max_tokens is not None:
                        max_tokens = user_override.max_tokens
                    if user_override.voice:
                        voice = user_override.voice

            except Exception as e:
                logger.warning("USER_OVERRIDE_FAILED", user_id=user_id, error=str(e))

        # Layer 2: Runtime overrides (highest precedence)
        if runtime_overrides:
            if "model" in runtime_overrides:
                model = runtime_overrides["model"]
            if "system_prompt" in runtime_overrides:
                system_prompt = runtime_overrides["system_prompt"]
            if "temperature" in runtime_overrides:
                temperature = float(runtime_overrides["temperature"])
            if "max_tokens" in runtime_overrides:
                max_tokens = int(runtime_overrides["max_tokens"])
            if "voice" in runtime_overrides:
                voice = runtime_overrides["voice"]

        return PersonaConfig(
            persona=persona,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            description=template.description,
            voice=voice,
            template_sha256=template.template_sha256,
            template_version=template.template_version,
        )

    # Backward compatibility alias
    def get_user_persona(self, persona: str, user_id: str, db: Session) -> PersonaConfig:
        """Get persona with user overrides (backward compatible)."""
        return self.get_effective_persona(persona, user_id=user_id, db=db)

    # ========================================================================
    # MULTI-TENANT MANAGEMENT
    # ========================================================================

    def clone_personas_for_user(self, user_id: str, db: Session) -> list[str]:
        """Clone all template personas for a new user."""
        from backend.models.db_models import UserPersonaConfig

        cloned = []

        for persona_id in self.list_personas():
            existing = (
                db.query(UserPersonaConfig)
                .filter_by(user_id=user_id, persona_id=persona_id)
                .first()
            )

            if existing is not None:
                continue

            config = UserPersonaConfig(
                user_id=user_id,
                persona_id=persona_id,
                custom_prompt=None,
                temperature=None,
                max_tokens=None,
                is_active=True,
            )
            db.add(config)
            cloned.append(persona_id)

        db.commit()
        logger.info("PERSONAS_CLONED", user_id=user_id, count=len(cloned))
        return cloned

    def update_user_persona(
        self,
        user_id: str,
        persona_id: str,
        db: Session,
        model: str | None = None,
        custom_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        voice: str | None = None,
    ) -> PersonaConfig:
        """Update user's persona overrides."""
        from backend.models.db_models import UserPersonaConfig

        # Verify persona exists
        self.get_persona(persona_id)

        config = (
            db.query(UserPersonaConfig).filter_by(user_id=user_id, persona_id=persona_id).first()
        )

        if config is None:
            config = UserPersonaConfig(
                user_id=user_id,
                persona_id=persona_id,
                model=model,
                custom_prompt=custom_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                voice=voice,
                is_active=True,
            )
            db.add(config)
        else:
            if model is not None:
                config.model = model
            if custom_prompt is not None:
                config.custom_prompt = custom_prompt
            if temperature is not None:
                config.temperature = temperature
            if max_tokens is not None:
                config.max_tokens = max_tokens
            if voice is not None:
                config.voice = voice

        db.commit()
        db.refresh(config)

        logger.info(
            "USER_PERSONA_UPDATED",
            user_id=user_id,
            persona_id=persona_id,
        )

        return self.get_effective_persona(persona_id, user_id=user_id, db=db)
