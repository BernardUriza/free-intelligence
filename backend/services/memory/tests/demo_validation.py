#!/usr/bin/env python3.14
"""Demo script showing MemoryStoreConfig validation in action.

Run: python3.14 backend/services/memory/tests/demo_validation.py

Author: Claude Code
Created: 2026-01-31
"""

from backend.services.memory.dependencies import MemoryStoreConfig, get_memory_config
from pydantic import ValidationError


def demo_valid_configs():
    """✅ Valid configurations."""
    print("=" * 60)
    print("✅ VALID CONFIGURATIONS")
    print("=" * 60)

    # HDF5 config (default)
    config1 = MemoryStoreConfig(use_elasticsearch=False, cache_size=1000)
    print(f"1. HDF5 Config: cache_size={config1.cache_size}")

    # Elasticsearch config with URL
    config2 = MemoryStoreConfig(
        use_elasticsearch=True,
        elasticsearch_url="http://localhost:9200",
        cache_size=256,
    )
    print(f"2. ES Config: url={config2.elasticsearch_url}, cache={config2.cache_size}")

    # From environment variables
    config3 = get_memory_config()
    print(
        f"3. From Env: elasticsearch={config3.use_elasticsearch}, cache={config3.cache_size}\n"
    )


def demo_invalid_configs():
    """❌ Invalid configurations (show validation errors)."""
    print("=" * 60)
    print("❌ INVALID CONFIGURATIONS (ValidationError Expected)")
    print("=" * 60)

    # Test 1: Negative cache size
    print("1. Negative cache_size:")
    try:
        MemoryStoreConfig(use_elasticsearch=False, cache_size=-100)
        print("   ⚠️  ERROR: Should have raised ValidationError!")
    except ValidationError as e:
        errors = e.errors()
        print(f"   ✅ ValidationError: {errors[0]['msg']}")

    # Test 2: Zero cache size
    print("\n2. Zero cache_size:")
    try:
        MemoryStoreConfig(use_elasticsearch=False, cache_size=0)
        print("   ⚠️  ERROR: Should have raised ValidationError!")
    except ValidationError as e:
        errors = e.errors()
        print(f"   ✅ ValidationError: {errors[0]['msg']}")

    # Test 3: Invalid URL format
    print("\n3. Invalid elasticsearch_url:")
    try:
        MemoryStoreConfig(
            use_elasticsearch=True,
            elasticsearch_url="not-a-valid-url",
            cache_size=128,
        )
        print("   ⚠️  ERROR: Should have raised ValidationError!")
    except ValidationError as e:
        print(f"   ✅ ValidationError: Invalid URL format")

    # Test 4: Missing URL when elasticsearch enabled
    print("\n4. use_elasticsearch=True but no URL:")
    try:
        MemoryStoreConfig(
            use_elasticsearch=True, elasticsearch_url=None, cache_size=128
        )
        print("   ⚠️  ERROR: Should have raised ValidationError!")
    except ValidationError as e:
        errors = e.errors()
        # Find the cross-field validation error
        for error in errors:
            if "required when use_elasticsearch" in str(error["msg"]):
                print(f"   ✅ ValidationError: {error['msg']}")
                break


def demo_immutability():
    """🔒 Immutability (frozen=True)."""
    print("\n" + "=" * 60)
    print("🔒 IMMUTABILITY (frozen=True)")
    print("=" * 60)

    config = MemoryStoreConfig(use_elasticsearch=False, cache_size=1000)
    print(f"Original cache_size: {config.cache_size}")

    print("\nAttempting to modify cache_size:")
    try:
        config.cache_size = 2000  # Should fail
        print("   ⚠️  ERROR: Should have raised ValidationError!")
    except ValidationError:
        print("   ✅ ValidationError: Frozen model cannot be modified")


def main():
    """Run all demos."""
    demo_valid_configs()
    demo_invalid_configs()
    demo_immutability()

    print("\n" + "=" * 60)
    print("✅ ALL VALIDATION DEMOS COMPLETE")
    print("=" * 60)
    print("\nPattern successfully implemented:")
    print("  - Type-safe config with Pydantic BaseModel")
    print("  - Declarative validation (Field constraints)")
    print("  - Cross-field validation (field_validator)")
    print("  - Immutable config (frozen=True)")
    print("  - Clear error messages (ValidationError)")


if __name__ == "__main__":
    main()
