"""KATNISS API Router.

KATNISS AI analysis endpoints

File: backend/api/katniss/router.py
Created: 2025-11-08
"""

from __future__ import annotations

import logging
import os

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/katniss", tags=["katniss"])

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2:7b")


class SessionData(BaseModel):
    duration: int  # minutos
    rpe: int  # 1-10
    emotionalCheckIn: str  # happy, neutral, tired
    notes: str = ""
    athleteName: str = "Deportista"


class KATNISSResponse(BaseModel):
    motivation: str
    nextSuggestion: str
    dayRecommended: str


@router.post("/analyze", response_model=KATNISSResponse)
async def analyze_session(session_data: SessionData):
    """
    Analiza datos de sesión con Ollama y genera feedback
    """
    try:
        # Construir prompt
        prompt = build_prompt(session_data)

        # Llamar a Ollama
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.7,
                },
            )

            if response.status_code != 200:
                logger.error(f"Ollama error: {response.text}")
                # Fallback si Ollama falla
                return get_fallback_response(session_data)

            data = response.json()
            return parse_ollama_response(data.get("response", ""), session_data)

    except Exception as e:
        logger.error(f"KATNISS analysis error: {e}")
        # Fallback response
        return get_fallback_response(session_data)


def build_prompt(session_data: SessionData) -> str:
    emotion_map = {
        "happy": "¡Excelente!",
        "neutral": "Bien",
        "tired": "Cansado",
    }

    emotion_label = emotion_map.get(session_data.emotionalCheckIn, "Bien")

    return f"""Eres KATNISS, un entrenador de IA empático para personas con T21 (síndrome de Down).

El deportista {session_data.athleteName} ha completado una sesión de entrenamiento con estos datos:
- Duración: {session_data.duration} minutos
- Esfuerzo percibido (RPE): {session_data.rpe}/10
- Estado emocional: {emotion_label}
{f'- Notas: {session_data.notes}' if session_data.notes else ''}

Genera en formato JSON VÁLIDO (sin markdown, sin explicaciones extras):
{{
  "motivation": "Una frase corta y motivadora (máx 15 palabras, en español simple, sin PHI)",
  "nextSuggestion": "Sugerencia concisa para próxima sesión (máx 12 palabras)",
  "dayRecommended": "Ej: 'mañana' o 'en 2 días' (recomendación de cuándo entrenar next)"
}}

IMPORTANTE:
- Usa lenguaje accesible (T21-friendly, simple, directo)
- Sé empático y motivador
- Responde SOLO el JSON, nada más"""


def parse_ollama_response(response_text: str, session_data: SessionData) -> KATNISSResponse:
    """
    Parsea respuesta de Ollama
    """
    import json
    import re

    try:
        # Buscar JSON en la respuesta
        json_match = re.search(r"\{[\s\S]*\}", response_text)
        if not json_match:
            return get_fallback_response(session_data)

        parsed = json.loads(json_match.group())
        return KATNISSResponse(
            motivation=parsed.get("motivation", "Great session!"),
            nextSuggestion=parsed.get("nextSuggestion", "Keep training regularly"),
            dayRecommended=parsed.get("dayRecommended", "tomorrow"),
        )
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        return get_fallback_response(session_data)


def get_fallback_response(session_data: SessionData) -> KATNISSResponse:
    """
    Respuesta por defecto si Ollama no está disponible
    """
    import random

    motivations = [
        "¡Lo hiciste increíble!",
        "¡Sigue adelante!",
        "¡Eres muy fuerte!",
        "¡Excelente trabajo!",
        "¡Puedes con todo!",
    ]

    suggestions = [
        "Descansa bien hoy",
        "Toma mucha agua",
        "Come frutas saludables",
        "Duerme 8 horas",
        "Sigue practicando",
    ]

    days = ["mañana", "en 2 días", "el fin de semana", "cuando quieras"]

    return KATNISSResponse(
        motivation=random.choice(motivations),
        nextSuggestion=random.choice(suggestions),
        dayRecommended=random.choice(days),
    )


@router.get("/health")
async def health_check():
    """
    Verifica si Ollama está disponible
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if response.status_code == 200:
                return {"status": "ok", "ollama": "connected", "model": OLLAMA_MODEL}
            else:
                return {"status": "error", "message": "Ollama not responding"}
    except Exception as e:
        logger.error(f"Ollama health check failed: {e}")
        return {"status": "error", "message": str(e)}
