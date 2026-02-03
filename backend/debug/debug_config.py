#!/usr/bin/env python3
"""
Script para verificar qué configuración está llegando al constructor de OllamaProvider
"""

import sys
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from backend.services.workflow.dependencies import get_policy_loader_dep


def main():
    print("🔍 Verificando el flujo de configuración a OllamaProvider")
    print("=" * 60)

    # Use singleton from DI (Phase 2.3 DI Refactor)
    policy_loader = get_policy_loader_dep()
    print(f"Proveedor primario de política: {policy_loader.get_primary_provider()}")

    # Obtener la configuración específica para Ollama
    ollama_config = policy_loader.get_provider_config("ollama")
    print(f"Configuración de Ollama desde política: {ollama_config}")
    print()

    # Verificar el modelo específico
    model_from_policy = ollama_config.get("model")
    print(f"Modelo desde política: '{model_from_policy}'")
    print(f"¿Es None? {model_from_policy is None}")
    print(f"¿Es string vacío? {model_from_policy == ''}")
    print(f"¿Es 'qwen3:1.7b'? {model_from_policy == 'qwen3:1.7b'}")
    print(f"¿Es 'qwen2.5:7b-instruct-q4_0'? {model_from_policy == 'qwen2.5:7b-instruct-q4_0'}")
    print()

    # Verificar qué otros valores hay en la configuración
    print("Otros valores en la configuración de Ollama:")
    for key, value in ollama_config.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
