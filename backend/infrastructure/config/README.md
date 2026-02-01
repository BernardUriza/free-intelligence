# Configuration Validation Pattern

**Pattern Established:** 2026-01-31
**First Implementation:** `backend/services/memory/dependencies.py` (MemoryStoreConfig)

---

## Why Pydantic for Config Validation?

### Problems with Dataclasses
```python
# ❌ BEFORE: @dataclass with no validation
@dataclass(frozen=True)
class OldConfig:
    cache_size: int  # No validation - accepts negative values

config = OldConfig(cache_size=-100)  # ☠️ Runtime error later
```

### Solution: Pydantic BaseModel
```python
# ✅ AFTER: Pydantic with declarative validation
from pydantic import BaseModel, ConfigDict, Field

class NewConfig(BaseModel):
    cache_size: int = Field(gt=0, default=128)
    model_config = ConfigDict(frozen=True)

config = NewConfig(cache_size=-100)  # ✅ ValidationError raised immediately
```

### Benefits
1. **Fail-Fast** - Invalid config detected at startup (not in production)
2. **Type-Safe** - Pyright validates all field access
3. **Clear Errors** - Pydantic error messages are descriptive
4. **Immutable** - `frozen=True` prevents accidental mutations
5. **Industry Standard** - Same validation used by FastAPI

---

## Pattern: Type-Safe Config Class

All config classes should follow this pattern:

```python
from pydantic import BaseModel, ConfigDict, Field, field_validator, HttpUrl

class MyServiceConfig(BaseModel):
    """Type-safe configuration with validation.

    Validation Rules:
        - api_key: Must be at least 32 characters
        - timeout_seconds: Must be > 0
        - base_url: Must be valid HTTP(S) URL
    """

    api_key: str = Field(min_length=32, description="Service API key")
    timeout_seconds: int = Field(gt=0, default=30, description="Request timeout")
    base_url: HttpUrl = Field(description="Service base URL")

    @field_validator("api_key")
    @classmethod
    def validate_api_key_format(cls, v: str) -> str:
        """Ensure API key has valid prefix."""
        if not v.startswith("sk-"):
            raise ValueError("api_key must start with 'sk-'")
        return v

    model_config = ConfigDict(frozen=True)
```

---

## Pattern: Environment Variable Parsing

```python
import os
from backend.infrastructure.config.base_config import BaseConfig

def get_my_config() -> MyServiceConfig:
    """Get configuration from environment variables.

    Environment Variables:
        API_KEY - Service API key (required)
        TIMEOUT - Request timeout in seconds (default: 30)
        BASE_URL - Service base URL (required)

    Returns:
        MyServiceConfig instance (immutable, validated)

    Raises:
        ValidationError: If configuration is invalid
    """
    api_key = os.getenv("API_KEY", "")  # Empty triggers validation error
    timeout = BaseConfig.parse_env_int("TIMEOUT", default=30, min_value=1)
    base_url = os.getenv("BASE_URL", "http://localhost:8000")

    return MyServiceConfig(
        api_key=api_key,
        timeout_seconds=timeout,
        base_url=base_url,
    )
```

---

## Common Validation Patterns

### 1. Range Validation
```python
cache_size: int = Field(gt=0, le=10000)  # 1 <= cache_size <= 10000
```

### 2. String Length
```python
api_key: str = Field(min_length=32, max_length=128)
```

### 3. URL Validation
```python
from pydantic import HttpUrl

elasticsearch_url: HttpUrl  # Validates HTTP(S) format
```

### 4. Cross-Field Validation
```python
@field_validator("elasticsearch_url")
@classmethod
def validate_es_url_required(cls, v: HttpUrl | None, info) -> HttpUrl | None:
    """Ensure elasticsearch_url provided when use_elasticsearch=True."""
    if info.data.get("use_elasticsearch") and not v:
        raise ValueError("elasticsearch_url required when use_elasticsearch=True")
    return v
```

### 5. Enum Validation
```python
from enum import Enum

class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    ERROR = "error"

class MyConfig(BaseModel):
    log_level: LogLevel = Field(default=LogLevel.INFO)
```

---

## Testing Pattern

All config classes should have comprehensive tests:

```python
import pytest
from pydantic import ValidationError

class TestMyServiceConfig:
    """Test Pydantic validation rules."""

    def test_valid_config(self):
        """✅ Valid config with all fields."""
        config = MyServiceConfig(
            api_key="sk-1234567890abcdef1234567890abcdef",
            timeout_seconds=60,
            base_url="https://api.service.com",
        )
        assert config.timeout_seconds == 60

    def test_negative_timeout_raises(self):
        """❌ Negative timeout should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            MyServiceConfig(
                api_key="sk-1234567890abcdef1234567890abcdef",
                timeout_seconds=-10,
                base_url="https://api.service.com",
            )

        error = exc_info.value.errors()[0]
        assert error["loc"] == ("timeout_seconds",)
        assert "greater than 0" in str(error["msg"])

    def test_config_immutable(self):
        """✅ frozen=True prevents field modification."""
        config = MyServiceConfig(...)

        with pytest.raises(ValidationError):
            config.timeout_seconds = 120  # Should fail
```

---

## Migration Checklist

When migrating existing `@dataclass` configs to Pydantic:

- [ ] Replace `from dataclasses import dataclass` with `from pydantic import BaseModel, ConfigDict, Field`
- [ ] Change `@dataclass(frozen=True)` to `class Config(BaseModel)` with `model_config = ConfigDict(frozen=True)`
- [ ] Add `Field()` constraints for all fields (gt, lt, min_length, etc.)
- [ ] Add `field_validator` for cross-field validation
- [ ] Write unit tests for validation (14+ test cases minimum)
- [ ] Update imports in consuming code (should be no changes if API unchanged)
- [ ] Run type checker (`pyright`) to verify no errors
- [ ] Run tests with coverage (`pytest --cov`)

---

## Success Metrics

After implementing this pattern:

- ✅ Cache size validation prevents negative/zero values
- ✅ URL validation prevents malformed URLs
- ✅ Cross-field validation enforces consistency
- ✅ 14+ unit tests pass (100% coverage)
- ✅ Pyright reports 0 errors
- ✅ Backward compatible (existing code works)
- ✅ Clear error messages on invalid config

---

## References

- **Pydantic Docs:** https://docs.pydantic.dev/latest/
- **Field Constraints:** https://docs.pydantic.dev/latest/concepts/fields/
- **Validators:** https://docs.pydantic.dev/latest/concepts/validators/
- **Migration Guide:** https://docs.pydantic.dev/latest/migration/

---

**Implementation Example:** See `backend/services/memory/dependencies.py` (lines 40-92) for full working example.
