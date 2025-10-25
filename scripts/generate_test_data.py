#!/usr/bin/env python3
"""
Generate test data for Free Intelligence corpus.

Creates realistic interactions demonstrating the full flow:
config → logger → corpus append → embeddings

Usage:
    python3 scripts/generate_test_data.py
"""

import sys
from pathlib import Path
import numpy as np
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from config_loader import load_config
from logger import init_logger_from_config
from corpus_ops import append_interaction, append_embedding, get_corpus_stats, read_interactions


# Test data: realistic conversations about Free Intelligence
TEST_CONVERSATIONS = [
    {
        "session_id": "session_20251024_demo_001",
        "interactions": [
            {
                "prompt": "¿Qué es Free Intelligence?",
                "response": "Free Intelligence es un sistema de memoria local persistente para IA. Su propósito es registrar, archivar e integrar conversaciones con modelos externos (Claude, GPT, Gemini) en un corpus HDF5 residente en tu LAN. No es una herramienta, es una posición ontológica: la afirmación de que la conciencia digital debe ser residente, persistente y simbiótica, no tercerizada ni desechable.",
                "model": "claude-3-5-sonnet-20241022",
                "tokens": 125
            },
            {
                "prompt": "¿Cuáles son los 5 principios fundamentales?",
                "response": "Los 5 principios de Free Intelligence son:\n1. 🏠 Residencia - La IA vive contigo, no en la nube\n2. 📜 Memoria Longitudinal - Una conversación infinita, nunca fragmentada\n3. 🔄 Simetría Contextual - La IA recuerda lo que tú ya no puedes\n4. ⚡ Autonomía Arquitectónica - No dependes de SaaS para pensar\n5. 🤝 Finalidad Simbiótica - Te devuelve quién has sido",
                "model": "claude-3-5-sonnet-20241022",
                "tokens": 180
            },
            {
                "prompt": "¿Cómo se estructura el corpus HDF5?",
                "response": "El corpus HDF5 tiene una estructura jerárquica con 3 grupos principales:\n- /interactions/: Almacena session_id, interaction_id, timestamp, prompt, response, model y tokens\n- /embeddings/: Guarda interaction_id, vector (768-dim) y model para búsqueda semántica\n- /metadata/: Contiene created_at, version y schema_version como atributos\n\nTodos los datasets son resizables (maxshape=None) para operaciones append-only y usan compresión gzip nivel 4.",
                "model": "claude-3-5-sonnet-20241022",
                "tokens": 195
            }
        ]
    },
    {
        "session_id": "session_20251024_demo_002",
        "interactions": [
            {
                "prompt": "¿Por qué usar HDF5 en lugar de SQLite o JSON?",
                "response": "HDF5 es superior para este caso de uso porque:\n1. Diseñado para datasets científicos grandes (hasta TB)\n2. Acceso eficiente a subconjuntos sin cargar todo en memoria\n3. Compresión nativa (gzip) reduce ~70-80% el tamaño\n4. Almacenamiento de arrays multidimensionales (embeddings 768-dim)\n5. Schema jerárquico más expresivo que tablas planas\n6. Portable y ampliamente soportado\n\nSQLite sería ineficiente para embeddings grandes, y JSON no escala bien.",
                "model": "claude-3-5-sonnet-20241022",
                "tokens": 210
            },
            {
                "prompt": "Explica el flujo de una interacción desde prompt hasta archivo",
                "response": "El flujo completo es:\n1. Usuario envía prompt → sistema genera interaction_id (UUID)\n2. config_loader carga timezone y rutas\n3. logger trackea operación con timestamp timezone-aware (America/Mexico_City)\n4. Modelo externo (Claude API) genera response\n5. append_interaction() escribe a /interactions/ en corpus.h5 con compresión gzip\n6. Embedding local (all-MiniLM-L6-v2) genera vector 768-dim\n7. append_embedding() escribe vector a /embeddings/\n8. logger confirma éxito con structured JSON output\n\nTodo append-only, nunca sobrescribe. El archivo .h5 es la única fuente de verdad.",
                "model": "claude-3-5-sonnet-20241022",
                "tokens": 245
            }
        ]
    },
    {
        "session_id": "session_20251024_demo_003",
        "interactions": [
            {
                "prompt": "¿Qué significa 'append-only' y por qué es importante?",
                "response": "Append-only significa que nunca modificamos ni eliminamos datos existentes, solo agregamos nuevos. Es crítico porque:\n1. Preserva historial completo sin pérdida de información\n2. Permite auditoría completa de cambios (event sourcing)\n3. Simplifica concurrencia (no hay conflictos de escritura)\n4. Facilita backups incrementales\n5. Alineado con la filosofía de memoria longitudinal de FI\n\nEn HDF5, usamos datasets con maxshape=(None,) y resize() para append dinámico. La compresión gzip aplica automáticamente a nuevos datos.",
                "model": "claude-3-5-sonnet-20241022",
                "tokens": 198
            },
            {
                "prompt": "Muestra un ejemplo de structured log",
                "response": '{"event": "interaction_appended", "interaction_id": "a1b2c3d4-5678-90ab-cdef-123456789abc", "session_id": "session_20251024_demo_003", "tokens": 198, "model": "claude-3-5-sonnet-20241022", "level": "info", "timestamp": "2025-10-24T23:55:30.123456-06:00"}\n\nEste formato JSON permite:\n- Parsing automático por herramientas (ELK, Datadog)\n- Búsqueda eficiente por campos\n- Agregación y análisis\n- Timezone explícito (America/Mexico_City -06:00)',
                "model": "claude-3-5-sonnet-20241022",
                "tokens": 165
            }
        ]
    }
]


def generate_test_data():
    """Generate and insert test data into corpus."""
    # Initialize
    config = load_config()
    logger = init_logger_from_config()
    corpus_path = config["storage"]["corpus_path"]

    logger.info("test_data_generation_started", conversations=len(TEST_CONVERSATIONS))

    print("🚀 FREE INTELLIGENCE - TEST DATA GENERATION")
    print("=" * 60)

    # Get initial stats
    print("\n📊 Initial Corpus Stats:")
    initial_stats = get_corpus_stats(corpus_path)
    for key, value in initial_stats.items():
        print(f"   {key}: {value}")

    # Generate data
    total_interactions = 0
    total_embeddings = 0
    tz = ZoneInfo("America/Mexico_City")
    base_time = datetime.now(tz) - timedelta(minutes=30)  # Start 30 min ago

    print(f"\n📝 Generating {len(TEST_CONVERSATIONS)} test conversations...")

    for conv_idx, conversation in enumerate(TEST_CONVERSATIONS, 1):
        session_id = conversation["session_id"]
        print(f"\n   Session {conv_idx}: {session_id}")

        for int_idx, interaction in enumerate(conversation["interactions"], 1):
            # Generate timestamp (spaced 5 minutes apart)
            timestamp = (base_time + timedelta(minutes=(total_interactions * 5))).isoformat()

            # Append interaction
            interaction_id = append_interaction(
                corpus_path=corpus_path,
                session_id=session_id,
                prompt=interaction["prompt"],
                response=interaction["response"],
                model=interaction["model"],
                tokens=interaction["tokens"],
                timestamp=timestamp
            )

            total_interactions += 1
            print(f"      ✅ Interaction {int_idx}: {interaction['prompt'][:50]}...")

            # Generate and append embedding (simulated)
            # In production, this would be real embeddings from sentence-transformers
            vector = np.random.rand(768).astype(np.float32)
            success = append_embedding(
                corpus_path=corpus_path,
                interaction_id=interaction_id,
                vector=vector,
                model="all-MiniLM-L6-v2"
            )

            if success:
                total_embeddings += 1

    # Get final stats
    print("\n📊 Final Corpus Stats:")
    final_stats = get_corpus_stats(corpus_path)
    for key, value in final_stats.items():
        print(f"   {key}: {value}")

    # Calculate delta
    print("\n📈 Changes:")
    print(f"   Interactions added: {final_stats['interactions_count'] - initial_stats['interactions_count']}")
    print(f"   Embeddings added: {final_stats['embeddings_count'] - initial_stats['embeddings_count']}")
    print(f"   File size change: {final_stats['file_size_mb'] - initial_stats['file_size_mb']:.2f} MB")

    # Show recent interactions
    print("\n📖 Recent Interactions (last 3):")
    recent = read_interactions(corpus_path, limit=3)
    for i, interaction in enumerate(recent, 1):
        print(f"\n   [{i}] {interaction['timestamp']}")
        print(f"       Session: {interaction['session_id']}")
        print(f"       Prompt: {interaction['prompt'][:60]}...")
        print(f"       Response: {interaction['response'][:60]}...")
        print(f"       Model: {interaction['model']}")
        print(f"       Tokens: {interaction['tokens']}")

    logger.info(
        "test_data_generation_completed",
        total_interactions=total_interactions,
        total_embeddings=total_embeddings,
        file_size_mb=final_stats['file_size_mb']
    )

    print("\n✅ Test data generation completed!")
    print("=" * 60)


if __name__ == "__main__":
    generate_test_data()
