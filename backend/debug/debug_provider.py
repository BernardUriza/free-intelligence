#!/usr/bin/env python3
from __future__ import annotations

"""
Script de depuración para verificar cómo se carga el proveedor Ollama
"""

import sys
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from backend.services.workflow.dependencies import get_policy_loader_dep
from backend.providers.llm import get_provider


def main():
    print("🔍 Debugging Ollama Provider Configuration")
    print("=" * 50)

    # Use singleton from DI (Phase 2.3 DI Refactor)
    policy_loader = get_policy_loader_dep()
    print(f"📦 Primary provider: {policy_loader.get_primary_provider()}")

    # Obtener la configuración de Ollama
    ollama_config = policy_loader.get_provider_config("ollama")
    print(f"⚙️  Ollama config: {ollama_config}")

    # Crear el proveedor con la configuración
    print("\n🔧 Creating Ollama provider with policy config...")
    try:
        ollama_provider = get_provider("ollama", ollama_config)
        print("✅ Provider created successfully")
        print(f"   - Model: {getattr(ollama_provider, 'default_model', None)}")
        print(f"   - Base URL: {getattr(ollama_provider, 'base_url', None)}")
    except Exception as e:
        print(f"❌ Error creating provider: {e}")
        import traceback

        traceback.print_exc()

    print("\n🔍 Comparing with direct config access...")
    model_from_config = ollama_config.get("model")
    print(f"   - Model from policy config: {model_from_config}")
    print("   - Expected model: qwen3:1.7b")


if __name__ == "__main__":
    main()
