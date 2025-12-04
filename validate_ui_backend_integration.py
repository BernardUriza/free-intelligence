#!/usr/bin/env python3
"""
Free Intelligence - UI/Backend Integration Validator

Validates the complete integration between UI and backend components.
Confirms that both systems are working in coordination.
"""

import sys
from pathlib import Path

import requests

# Add project root to path to access backend modules
sys.path.insert(0, str(Path(__file__).parent))


def validate_ui_backend_integration():
    """Validates that UI and backend are properly integrated"""

    print("🏥 Validando integración UI-Backend Free Intelligence")
    print("=" * 60)

    # 1. Validate backend health
    print("🔍 Validando salud del backend...")
    try:
        backend_response = requests.get("http://localhost:7001/health", timeout=10)
        if backend_response.status_code == 200:
            print("✅ Backend saludable: http://localhost:7001/health")
            backend_healthy = True
        else:
            print(f"❌ Backend no saludable: {backend_response.status_code}")
            backend_healthy = False
    except Exception as e:
        print(f"❌ Error conectando con backend: {e}")
        backend_healthy = False

    # 2. Validate UI is accessible
    print("\n🔍 Validando UI accesible...")
    try:
        ui_response = requests.get("http://localhost:9000", timeout=10)
        if ui_response.status_code == 200:
            print("✅ UI accesible: http://localhost:9000")
            ui_accessible = True
        else:
            print(f"❌ UI no accesible: {ui_response.status_code}")
            ui_accessible = False
    except Exception as e:
        print(f"❌ Error conectando con UI: {e}")
        ui_accessible = False

    # 3. Validate internal LLM endpoint (protected)
    print("\n🔍 Validando endpoint de LLM interno...")
    try:
        internal_response = requests.get("http://localhost:7001/internal/llm/health", timeout=10)
        if internal_response.status_code == 200:
            print("✅ Endpoint LLM interno accesible")
            internal_healthy = True
        else:
            print(f"⚠️  Endpoint LLM interno no accesible: {internal_response.status_code}")
            internal_healthy = False
    except Exception as e:
        print(f"⚠️  Error con endpoint LLM interno: {e}")
        internal_healthy = False

    # 4. Test structured extraction endpoint
    print("\n🔍 Validando endpoint de asistente SOAP...")
    try:
        extraction_payload = {
            "command": "Agregar que el paciente tiene hipertensión arterial",
            "current_soap": {
                "subjective": "Paciente refiere dolor de cabeza ocasional",
                "objective": {"pressure": "140/90"},
                "assessment": "Dolor de cabeza, posible hipertensión",
                "plan": {"studies": ["presión arterial"]},
            },
        }

        extraction_response = requests.post(
            "http://localhost:7001/api/workflows/aurity/sessions/test_validation/assistant",
            json=extraction_payload,
            timeout=30,
        )

        if extraction_response.status_code == 200:
            print("✅ Endpoint de asistente SOAP funcionando")
            extraction_working = True
        else:
            print(
                f"⚠️  Endpoint de asistente SOAP no funcionando: {extraction_response.status_code}"
            )
            print(f"   Response: {extraction_response.text[:200]}...")
            extraction_working = False
    except Exception as e:
        print(f"⚠️  Error con endpoint de asistente SOAP: {e}")
        extraction_working = False

    # 5. Check for Ollama availability
    print("\n🔍 Validando disponibilidad de Ollama...")
    try:
        ollama_response = requests.get("http://localhost:11434/api/tags", timeout=10)
        if ollama_response.status_code == 200:
            models = ollama_response.json().get("models", [])
            if models:
                print(f"✅ Ollama disponible con {len(models)} modelo(s)")
                ollama_available = True
            else:
                print("⚠️  Ollama disponible pero sin modelos")
                ollama_available = False
        else:
            print(f"⚠️  Ollama no disponible: {ollama_response.status_code}")
            ollama_available = False
    except Exception as e:
        print(f"⚠️  Error conectando con Ollama: {e}")
        ollama_available = False

    print("\n" + "=" * 60)
    print("📊 RESULTADOS DE VALIDACIÓN")
    print("=" * 60)
    print(f"Backend saludable: {'✅' if backend_healthy else '❌'}")
    print(f"UI accesible: {'✅' if ui_accessible else '❌'}")
    print(f"Endpoint LLM interno: {'✅' if internal_healthy else '❌'}")
    print(f"Extracción estructurada: {'✅' if extraction_working else '❌'}")
    print(f"Ollama disponible: {'✅' if ollama_available else '❌'}")

    all_working = all(
        [backend_healthy, ui_accessible, internal_healthy, extraction_working, ollama_available]
    )

    print(f"\n🎯 INTEGRACIÓN COMPLETA: {'✅ APROBADA' if all_working else '❌ CON ERRORES'}")

    if all_working:
        print("\n🎉 ¡Sistema Free Intelligence (AURITY) completamente operativo!")
        print("   - Backend API: http://localhost:7001")
        print("   - UI médica: http://localhost:9000")
        print("   - Proveedor Ollama: http://localhost:11434")
        print("   - Flujos médicos: Disponibles en UI")
        print("   - Extracción estructurada: Funcional")
    else:
        print("\n⚠️  El sistema tiene componentes no operativos. Revisa los errores anteriores.")

    return all_working


if __name__ == "__main__":
    success = validate_ui_backend_integration()
    sys.exit(0 if success else 1)
