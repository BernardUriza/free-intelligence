#!/usr/bin/env python3
"""
Migration Script: DEFAULT_CONTENT → TV Content Seeds

Converts hardcoded DEFAULT_CONTENT from FIAvatar.tsx to editable JSON seeds.

Card: FI-TV-REFAC-001
Author: Bernard Uriza Orozco
Created: 2025-11-18

Usage:
    python3 scripts/migrate_tv_content_seeds.py
"""

import json
import time
import uuid
from pathlib import Path

# Storage path
SEEDS_STORAGE_PATH = Path("storage/tv_seeds")
SEEDS_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

# Default content from FIAvatar.tsx (lines 98-186)
DEFAULT_CONTENT_DATA = [
    {
        "type": "welcome",
        "content": "Bienvenidos a nuestra clínica. Free Intelligence está aquí para acompañarlos durante su espera.",
        "duration": 12000,
    },
    {
        "type": "widget",
        "content": "",
        "duration": 20000,
        "widget_type": "weather",
    },
    {
        "type": "philosophy",
        "content": "🏠 **Soberanía de Datos**: Sus datos médicos permanecen aquí, en esta clínica. Nunca salen del perímetro controlado por su doctor. Control total, privacidad garantizada.",
        "duration": 18000,
    },
    {
        "type": "widget",
        "content": "",
        "duration": 25000,
        "widget_type": "breathing",
    },
    {
        "type": "tip",
        "content": "💧 **Tip de Salud**: Mantenerse hidratado es esencial. Beba al menos 8 vasos de agua al día para una salud óptima.",
        "duration": 15000,
    },
    {
        "type": "widget",
        "content": "",
        "duration": 25000,
        "widget_type": "trivia",
        "widget_data": {
            "question": "¿Cuántos vasos de agua se recomienda beber al día para un adulto promedio?",
            "options": ["4-5 vasos", "6-7 vasos", "8-10 vasos", "12-15 vasos"],
            "correctAnswer": 2,
            "explanation": "Se recomienda beber entre 8 y 10 vasos de agua al día (aproximadamente 2 litros) para mantener una hidratación adecuada.",
        },
    },
    {
        "type": "tip",
        "content": "🚶 **Actividad Física**: 30 minutos de caminata diaria pueden reducir el riesgo de enfermedades cardíacas hasta en un 50%.",
        "duration": 15000,
    },
    {
        "type": "widget",
        "content": "",
        "duration": 20000,
        "widget_type": "calming",
    },
    {
        "type": "philosophy",
        "content": "⚡ **Latencia <50ms**: Procesamiento local en tiempo real. Sin esperas, sin dependencia de internet para funciones críticas.",
        "duration": 15000,
    },
    {
        "type": "widget",
        "content": "",
        "duration": 18000,
        "widget_type": "daily_tip",
        "widget_data": {
            "tip": "Incluir alimentos ricos en fibra como avena, frutas y verduras ayuda a mejorar la digestión y mantener niveles saludables de colesterol.",
            "category": "nutrition",
            "generatedBy": "static",
        },
    },
    {
        "type": "tip",
        "content": "🥗 **Nutrición**: Una dieta balanceada con frutas y verduras de colores variados proporciona vitaminas y antioxidantes esenciales.",
        "duration": 15000,
    },
    {
        "type": "philosophy",
        "content": "🔒 **Encriptación AES-GCM-256**: Toda su información de salud está protegida con el mismo nivel de seguridad que usan los bancos.",
        "duration": 15000,
    },
    {
        "type": "tip",
        "content": "😴 **Sueño de Calidad**: Dormir 7-8 horas por noche mejora la memoria, el sistema inmune y reduce el estrés.",
        "duration": 15000,
    },
]


def create_seed(item: dict, display_order: int) -> dict:
    """
    Convert DEFAULT_CONTENT item to TVContentSeed schema.
    """
    now = int(time.time() * 1000)

    seed = {
        "content_id": str(uuid.uuid4()),
        "type": item["type"],
        "content": item.get("content", ""),
        "duration": item.get("duration", 15000),
        "widget_type": item.get("widget_type"),
        "widget_data": item.get("widget_data"),
        "is_system_default": True,  # FI seed
        "is_active": True,
        "display_order": display_order,
        "clinic_id": None,  # Global seed
        "created_at": now,
        "updated_at": now,
    }

    return seed


def migrate_seeds():
    """
    Migrate DEFAULT_CONTENT to JSON seed files.
    """
    print("🚀 Starting TV Content Seeds Migration...")
    print(f"📁 Target directory: {SEEDS_STORAGE_PATH.absolute()}")
    print(f"📊 Total items to migrate: {len(DEFAULT_CONTENT_DATA)}")
    print()

    migrated_count = 0

    for index, item in enumerate(DEFAULT_CONTENT_DATA):
        seed = create_seed(item, display_order=index)
        content_id = seed["content_id"]

        # Save to JSON file
        seed_file = SEEDS_STORAGE_PATH / f"{content_id}.json"
        with open(seed_file, "w", encoding="utf-8") as f:
            json.dump(seed, f, indent=2, ensure_ascii=False)

        migrated_count += 1

        # Log progress
        content_type = seed["type"]
        widget_type = seed.get("widget_type", "")
        label = f"{content_type}" + (f":{widget_type}" if widget_type else "")
        print(f"  ✅ [{index + 1:2d}/14] {label:30s} → {content_id}")

    print()
    print(f"✨ Migration complete! {migrated_count} seeds created.")
    print()
    print("Next steps:")
    print("  1. Register router in backend/app/main.py")
    print("  2. Update FIAvatar.tsx to fetch from /api/tv-content/list")
    print("  3. Test carousel with seeds + doctor media")
    print()


if __name__ == "__main__":
    migrate_seeds()
