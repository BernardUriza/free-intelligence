"""Conversational Check-in Service with Claude AI.

Guided conversational flow for patient self-service check-in.
Uses a state machine approach with Claude for NLU and response generation.

File: backend/services/checkin_conversation.py
Card: FI-CHECKIN-004
Created: 2025-11-22

Flow States:
    GREETING → CODE_INPUT → CODE_VERIFY → INFO_CONFIRM → COMPLETE

Design Philosophy:
    - State machine controls flow (prevents LLM from going off-script)
    - Claude handles: intent recognition, entity extraction, natural responses
    - Concise responses (anxious patients in medical settings)
    - Always offer human escalation option
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from backend.logger import get_logger

logger = get_logger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
CLAUDE_MODEL = os.getenv("CHECKIN_CLAUDE_MODEL", "claude-sonnet-4-20250514")


# =============================================================================
# CONVERSATION STATES
# =============================================================================


class ConversationState(str, Enum):
    """States in the check-in conversation flow."""

    GREETING = "greeting"
    CODE_INPUT = "code_input"
    CODE_VERIFY = "code_verify"
    NAME_INPUT = "name_input"
    INFO_CONFIRM = "info_confirm"
    PENDING_ACTIONS = "pending_actions"
    COMPLETE = "complete"
    ERROR = "error"
    HUMAN_ESCALATION = "human_escalation"


class UserIntent(str, Enum):
    """Recognized user intents."""

    PROVIDE_CODE = "provide_code"
    PROVIDE_NAME = "provide_name"
    CONFIRM_YES = "confirm_yes"
    CONFIRM_NO = "confirm_no"
    NEED_HELP = "need_help"
    UNKNOWN = "unknown"


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class ConversationContext:
    """Context maintained throughout the conversation."""

    session_id: str
    clinic_id: str
    state: ConversationState = ConversationState.GREETING
    patient_id: str | None = None
    patient_name: str | None = None
    appointment_id: str | None = None
    appointment_time: str | None = None
    doctor_name: str | None = None
    checkin_code: str | None = None
    attempts: int = 0
    max_attempts: int = 3
    messages: list[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_message(self, role: str, content: str) -> None:
        """Add a message to conversation history."""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(UTC).isoformat(),
        })
        self.last_updated = datetime.now(UTC)


@dataclass
class ConversationResponse:
    """Response from the conversation service."""

    message: str
    state: ConversationState
    requires_input: bool = True
    actions: list[dict] = field(default_factory=list)
    quick_replies: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# RESPONSE TEMPLATES (Spanish - Mexican clinic context)
# =============================================================================

RESPONSES = {
    ConversationState.GREETING: (
        "¡Hola! Bienvenido a {clinic_name}. 👋\n\n"
        "Soy el asistente virtual de check-in. "
        "Para comenzar, por favor ingrese su **código de cita de 6 dígitos**.\n\n"
        "_Si no tiene el código, puede proporcionarme su nombre completo._"
    ),
    ConversationState.CODE_INPUT: (
        "Por favor ingrese su código de cita de 6 dígitos.\n\n"
        "_Puede encontrarlo en el SMS o email de confirmación._"
    ),
    ConversationState.CODE_VERIFY: (
        "Verificando código **{code}**... ⏳"
    ),
    ConversationState.NAME_INPUT: (
        "Entendido. Por favor ingrese su **nombre completo** como aparece en su identificación."
    ),
    ConversationState.INFO_CONFIRM: (
        "Encontré su cita: ✅\n\n"
        "👤 **{patient_name}**\n"
        "📅 Hoy a las **{appointment_time}**\n"
        "👨‍⚕️ Dr. {doctor_name}\n\n"
        "¿Es correcto?"
    ),
    ConversationState.PENDING_ACTIONS: (
        "Antes de completar su check-in, necesitamos que complete lo siguiente:\n\n"
        "{actions_list}\n\n"
        "¿Ya completó estas acciones?"
    ),
    ConversationState.COMPLETE: (
        "✅ **Check-in completado**\n\n"
        "Por favor tome asiento en la sala de espera. "
        "Le llamaremos cuando sea su turno.\n\n"
        "Tiempo estimado de espera: **{wait_time} minutos**\n\n"
        "¡Que tenga una excelente consulta! 🏥"
    ),
    ConversationState.ERROR: (
        "Lo siento, no pude encontrar una cita con ese {identifier}. 😔\n\n"
        "Por favor verifique e intente nuevamente, o solicite ayuda en recepción."
    ),
    ConversationState.HUMAN_ESCALATION: (
        "Entendido. Un miembro del equipo de recepción le asistirá en breve. 🙋\n\n"
        "Por favor acérquese al mostrador de recepción."
    ),
}

QUICK_REPLIES = {
    ConversationState.GREETING: ["Tengo mi código", "No tengo código", "Necesito ayuda"],
    ConversationState.INFO_CONFIRM: ["Sí, es correcto", "No, hay un error"],
    ConversationState.PENDING_ACTIONS: ["Ya las completé", "Necesito ayuda"],
}


# =============================================================================
# INTENT RECOGNITION (Simple rule-based + Claude fallback)
# =============================================================================


def extract_checkin_code(text: str) -> str | None:
    """Extract 6-digit check-in code from text."""
    # Look for 6 consecutive digits
    match = re.search(r"\b(\d{6})\b", text)
    return match.group(1) if match else None


def recognize_intent(text: str, current_state: ConversationState) -> tuple[UserIntent, dict]:
    """Recognize user intent from input text.

    Returns:
        Tuple of (intent, extracted_entities)
    """
    text_lower = text.lower().strip()
    entities: dict[str, Any] = {}

    # Check for help/escalation requests
    help_keywords = ["ayuda", "help", "humano", "persona", "recepcion", "no entiendo"]
    if any(kw in text_lower for kw in help_keywords):
        return UserIntent.NEED_HELP, entities

    # Check for confirmation responses
    yes_keywords = ["sí", "si", "correcto", "exacto", "yes", "ok", "confirmo", "listo"]
    no_keywords = ["no", "incorrecto", "error", "mal", "equivocado"]

    if any(kw in text_lower for kw in yes_keywords) and not any(kw in text_lower for kw in no_keywords):
        return UserIntent.CONFIRM_YES, entities
    if any(kw in text_lower for kw in no_keywords):
        return UserIntent.CONFIRM_NO, entities

    # Check for check-in code
    code = extract_checkin_code(text)
    if code:
        entities["checkin_code"] = code
        return UserIntent.PROVIDE_CODE, entities

    # Check for name input (if in name input state or contains name-like patterns)
    if current_state == ConversationState.NAME_INPUT or len(text.split()) >= 2:
        # Assume multi-word input in NAME_INPUT state is a name
        if current_state == ConversationState.NAME_INPUT:
            entities["patient_name"] = text.strip()
            return UserIntent.PROVIDE_NAME, entities

    return UserIntent.UNKNOWN, entities


# =============================================================================
# CONVERSATION SERVICE
# =============================================================================


class CheckinConversationService:
    """Service for managing conversational check-in flow.

    Example usage:
        service = CheckinConversationService()
        context = service.start_conversation(session_id, clinic_id, clinic_name)
        response = await service.process_message(context, "123456")
    """

    def __init__(self) -> None:
        self._contexts: dict[str, ConversationContext] = {}
        self._claude_client = None

    def _get_claude_client(self):
        """Lazy-load Claude client."""
        if self._claude_client is None and CLAUDE_API_KEY:
            try:
                from anthropic import Anthropic
                self._claude_client = Anthropic(api_key=CLAUDE_API_KEY)
            except ImportError:
                logger.warning("ANTHROPIC_NOT_INSTALLED")
        return self._claude_client

    def start_conversation(
        self,
        session_id: str,
        clinic_id: str,
        clinic_name: str = "la clínica",
    ) -> ConversationResponse:
        """Start a new check-in conversation.

        Args:
            session_id: Unique session identifier
            clinic_id: Clinic UUID
            clinic_name: Display name of the clinic

        Returns:
            Initial greeting response
        """
        context = ConversationContext(
            session_id=session_id,
            clinic_id=clinic_id,
            state=ConversationState.GREETING,
            metadata={"clinic_name": clinic_name},
        )
        self._contexts[session_id] = context

        greeting = RESPONSES[ConversationState.GREETING].format(clinic_name=clinic_name)
        context.add_message("assistant", greeting)

        logger.info(
            "CHECKIN_CONVERSATION_STARTED",
            session_id=session_id,
            clinic_id=clinic_id,
        )

        return ConversationResponse(
            message=greeting,
            state=ConversationState.GREETING,
            quick_replies=QUICK_REPLIES.get(ConversationState.GREETING, []),
        )

    def get_context(self, session_id: str) -> ConversationContext | None:
        """Get conversation context by session ID."""
        return self._contexts.get(session_id)

    async def process_message(
        self,
        session_id: str,
        user_message: str,
        db_session=None,
    ) -> ConversationResponse:
        """Process a user message and return response.

        Args:
            session_id: Conversation session ID
            user_message: User's input text
            db_session: Optional database session for lookups

        Returns:
            ConversationResponse with next message and state
        """
        context = self._contexts.get(session_id)
        if not context:
            return ConversationResponse(
                message="Sesión no encontrada. Por favor inicie nuevamente.",
                state=ConversationState.ERROR,
                requires_input=False,
            )

        # Add user message to history
        context.add_message("user", user_message)

        # Recognize intent
        intent, entities = recognize_intent(user_message, context.state)

        logger.info(
            "CHECKIN_MESSAGE_RECEIVED",
            session_id=session_id,
            state=context.state.value,
            intent=intent.value,
            entities=list(entities.keys()),
        )

        # Handle based on current state and intent
        response = await self._handle_state_transition(context, intent, entities, db_session)

        # Add assistant response to history
        context.add_message("assistant", response.message)

        return response

    async def _handle_state_transition(
        self,
        context: ConversationContext,
        intent: UserIntent,
        entities: dict,
        db_session=None,
    ) -> ConversationResponse:
        """Handle state transitions based on current state and intent."""

        # Global: Handle help request from any state
        if intent == UserIntent.NEED_HELP:
            context.state = ConversationState.HUMAN_ESCALATION
            return ConversationResponse(
                message=RESPONSES[ConversationState.HUMAN_ESCALATION],
                state=ConversationState.HUMAN_ESCALATION,
                requires_input=False,
            )

        # State-specific handling
        match context.state:
            case ConversationState.GREETING:
                return self._handle_greeting(context, intent, entities)

            case ConversationState.CODE_INPUT:
                return await self._handle_code_input(context, intent, entities, db_session)

            case ConversationState.NAME_INPUT:
                return await self._handle_name_input(context, intent, entities, db_session)

            case ConversationState.INFO_CONFIRM:
                return self._handle_info_confirm(context, intent)

            case ConversationState.PENDING_ACTIONS:
                return self._handle_pending_actions(context, intent)

            case _:
                return ConversationResponse(
                    message="Estado no reconocido. Por favor solicite ayuda en recepción.",
                    state=ConversationState.ERROR,
                    requires_input=False,
                )

    def _handle_greeting(
        self,
        context: ConversationContext,
        intent: UserIntent,
        entities: dict,
    ) -> ConversationResponse:
        """Handle GREETING state transitions."""
        if intent == UserIntent.PROVIDE_CODE:
            # User provided code directly in greeting
            context.checkin_code = entities.get("checkin_code")
            context.state = ConversationState.CODE_INPUT
            return ConversationResponse(
                message=RESPONSES[ConversationState.CODE_VERIFY].format(code=context.checkin_code),
                state=ConversationState.CODE_INPUT,
                metadata={"code": context.checkin_code},
            )

        # Default: Ask for code
        context.state = ConversationState.CODE_INPUT
        return ConversationResponse(
            message=RESPONSES[ConversationState.CODE_INPUT],
            state=ConversationState.CODE_INPUT,
        )

    async def _handle_code_input(
        self,
        context: ConversationContext,
        intent: UserIntent,
        entities: dict,
        db_session=None,
    ) -> ConversationResponse:
        """Handle CODE_INPUT state - verify check-in code."""
        if intent == UserIntent.PROVIDE_CODE:
            code = entities.get("checkin_code")
            context.checkin_code = code

            # Verify code against database
            if db_session:
                appointment = await self._lookup_by_code(code, context.clinic_id, db_session)
                if appointment:
                    return self._transition_to_confirm(context, appointment)

            # Code not found - increment attempts
            context.attempts += 1
            if context.attempts >= context.max_attempts:
                context.state = ConversationState.HUMAN_ESCALATION
                return ConversationResponse(
                    message=(
                        "No pudimos verificar su código después de varios intentos. "
                        "Por favor acérquese a recepción para asistencia."
                    ),
                    state=ConversationState.HUMAN_ESCALATION,
                    requires_input=False,
                )

            return ConversationResponse(
                message=RESPONSES[ConversationState.ERROR].format(identifier="código"),
                state=ConversationState.CODE_INPUT,
                quick_replies=["Intentar de nuevo", "Usar mi nombre", "Necesito ayuda"],
            )

        # User wants to use name instead
        if "nombre" in context.messages[-1]["content"].lower() or intent == UserIntent.CONFIRM_NO:
            context.state = ConversationState.NAME_INPUT
            return ConversationResponse(
                message=RESPONSES[ConversationState.NAME_INPUT],
                state=ConversationState.NAME_INPUT,
            )

        return ConversationResponse(
            message="Por favor ingrese su código de 6 dígitos o diga 'nombre' para identificarse de otra forma.",
            state=ConversationState.CODE_INPUT,
        )

    async def _handle_name_input(
        self,
        context: ConversationContext,
        intent: UserIntent,
        entities: dict,
        db_session=None,
    ) -> ConversationResponse:
        """Handle NAME_INPUT state - verify by patient name."""
        if intent == UserIntent.PROVIDE_NAME:
            name = entities.get("patient_name")

            if db_session:
                appointment = await self._lookup_by_name(name, context.clinic_id, db_session)
                if appointment:
                    return self._transition_to_confirm(context, appointment)

            context.attempts += 1
            if context.attempts >= context.max_attempts:
                context.state = ConversationState.HUMAN_ESCALATION
                return ConversationResponse(
                    message=(
                        "No pudimos encontrar su cita. "
                        "Por favor acérquese a recepción para asistencia."
                    ),
                    state=ConversationState.HUMAN_ESCALATION,
                    requires_input=False,
                )

            return ConversationResponse(
                message=RESPONSES[ConversationState.ERROR].format(identifier="nombre"),
                state=ConversationState.NAME_INPUT,
                quick_replies=["Intentar de nuevo", "Necesito ayuda"],
            )

        return ConversationResponse(
            message="Por favor ingrese su nombre completo como aparece en su identificación.",
            state=ConversationState.NAME_INPUT,
        )

    def _handle_info_confirm(
        self,
        context: ConversationContext,
        intent: UserIntent,
    ) -> ConversationResponse:
        """Handle INFO_CONFIRM state - user confirms appointment details."""
        if intent == UserIntent.CONFIRM_YES:
            # Check for pending actions
            if context.metadata.get("pending_actions"):
                context.state = ConversationState.PENDING_ACTIONS
                actions = context.metadata["pending_actions"]
                actions_list = "\n".join([f"• {a}" for a in actions])
                return ConversationResponse(
                    message=RESPONSES[ConversationState.PENDING_ACTIONS].format(
                        actions_list=actions_list
                    ),
                    state=ConversationState.PENDING_ACTIONS,
                    quick_replies=QUICK_REPLIES.get(ConversationState.PENDING_ACTIONS, []),
                )

            # No pending actions - complete check-in
            return self._complete_checkin(context)

        if intent == UserIntent.CONFIRM_NO:
            context.state = ConversationState.HUMAN_ESCALATION
            return ConversationResponse(
                message=(
                    "Entendido. Si la información no es correcta, "
                    "por favor acérquese a recepción para verificar sus datos."
                ),
                state=ConversationState.HUMAN_ESCALATION,
                requires_input=False,
            )

        return ConversationResponse(
            message="Por favor confirme si la información es correcta respondiendo 'Sí' o 'No'.",
            state=ConversationState.INFO_CONFIRM,
            quick_replies=QUICK_REPLIES.get(ConversationState.INFO_CONFIRM, []),
        )

    def _handle_pending_actions(
        self,
        context: ConversationContext,
        intent: UserIntent,
    ) -> ConversationResponse:
        """Handle PENDING_ACTIONS state."""
        if intent == UserIntent.CONFIRM_YES:
            return self._complete_checkin(context)

        return ConversationResponse(
            message=(
                "Por favor complete las acciones pendientes antes de continuar, "
                "o solicite ayuda si necesita asistencia."
            ),
            state=ConversationState.PENDING_ACTIONS,
            quick_replies=["Ya las completé", "Necesito ayuda"],
        )

    def _transition_to_confirm(
        self,
        context: ConversationContext,
        appointment: dict,
    ) -> ConversationResponse:
        """Transition to INFO_CONFIRM state with appointment details."""
        context.patient_id = appointment.get("patient_id")
        context.patient_name = appointment.get("patient_name")
        context.appointment_id = appointment.get("appointment_id")
        context.appointment_time = appointment.get("appointment_time")
        context.doctor_name = appointment.get("doctor_name")
        context.metadata["pending_actions"] = appointment.get("pending_actions", [])

        context.state = ConversationState.INFO_CONFIRM

        return ConversationResponse(
            message=RESPONSES[ConversationState.INFO_CONFIRM].format(
                patient_name=context.patient_name,
                appointment_time=context.appointment_time,
                doctor_name=context.doctor_name or "Asignado",
            ),
            state=ConversationState.INFO_CONFIRM,
            quick_replies=QUICK_REPLIES.get(ConversationState.INFO_CONFIRM, []),
            metadata={
                "patient_id": context.patient_id,
                "appointment_id": context.appointment_id,
            },
        )

    def _complete_checkin(self, context: ConversationContext) -> ConversationResponse:
        """Complete the check-in process."""
        context.state = ConversationState.COMPLETE

        # Estimate wait time (placeholder - would come from queue analysis)
        wait_time = 15

        logger.info(
            "CHECKIN_CONVERSATION_COMPLETE",
            session_id=context.session_id,
            patient_id=context.patient_id,
            appointment_id=context.appointment_id,
        )

        return ConversationResponse(
            message=RESPONSES[ConversationState.COMPLETE].format(wait_time=wait_time),
            state=ConversationState.COMPLETE,
            requires_input=False,
            actions=[
                {
                    "type": "complete_checkin",
                    "appointment_id": context.appointment_id,
                    "patient_id": context.patient_id,
                }
            ],
        )

    async def _lookup_by_code(
        self,
        code: str,
        clinic_id: str,
        db_session,
    ) -> dict | None:
        """Look up appointment by check-in code.

        TODO(human): Implement actual database lookup
        """
        from sqlalchemy import text

        query = text("""
            SELECT
                a.appointment_id,
                a.scheduled_at,
                a.checkin_code,
                p.patient_id,
                p.nombre || ' ' || p.apellido as patient_name,
                d.display_name as doctor_name
            FROM appointments a
            JOIN patients p ON a.patient_id = p.patient_id
            LEFT JOIN doctors d ON a.doctor_id = d.doctor_id
            WHERE a.checkin_code = :code
              AND a.clinic_id = :clinic_id
              AND a.status = 'scheduled'
              AND a.checkin_code_expires_at > NOW()
        """)

        try:
            result = db_session.execute(
                query,
                {"code": code, "clinic_id": clinic_id}
            ).fetchone()

            if result:
                return {
                    "appointment_id": result.appointment_id,
                    "patient_id": result.patient_id,
                    "patient_name": result.patient_name,
                    "appointment_time": result.scheduled_at.strftime("%H:%M"),
                    "doctor_name": result.doctor_name,
                    "pending_actions": [],  # Would come from pending_actions table
                }
        except Exception as e:
            logger.error("CHECKIN_CODE_LOOKUP_FAILED", error=str(e))

        return None

    async def _lookup_by_name(
        self,
        name: str,
        clinic_id: str,
        db_session,
    ) -> dict | None:
        """Look up appointment by patient name.

        TODO(human): Implement fuzzy name matching
        """
        from sqlalchemy import text

        # Simple name match (case-insensitive)
        query = text("""
            SELECT
                a.appointment_id,
                a.scheduled_at,
                a.checkin_code,
                p.patient_id,
                p.nombre || ' ' || p.apellido as patient_name,
                d.display_name as doctor_name
            FROM appointments a
            JOIN patients p ON a.patient_id = p.patient_id
            LEFT JOIN doctors d ON a.doctor_id = d.doctor_id
            WHERE LOWER(p.nombre || ' ' || p.apellido) LIKE LOWER(:name)
              AND a.clinic_id = :clinic_id
              AND a.status = 'scheduled'
              AND DATE(a.scheduled_at) = CURRENT_DATE
            ORDER BY a.scheduled_at
            LIMIT 1
        """)

        try:
            result = db_session.execute(
                query,
                {"name": f"%{name}%", "clinic_id": clinic_id}
            ).fetchone()

            if result:
                return {
                    "appointment_id": result.appointment_id,
                    "patient_id": result.patient_id,
                    "patient_name": result.patient_name,
                    "appointment_time": result.scheduled_at.strftime("%H:%M"),
                    "doctor_name": result.doctor_name,
                    "pending_actions": [],
                }
        except Exception as e:
            logger.error("CHECKIN_NAME_LOOKUP_FAILED", error=str(e))

        return None

    def end_conversation(self, session_id: str) -> None:
        """End and clean up a conversation session."""
        if session_id in self._contexts:
            del self._contexts[session_id]
            logger.info("CHECKIN_CONVERSATION_ENDED", session_id=session_id)


# =============================================================================
# MODULE-LEVEL INSTANCE
# =============================================================================

checkin_conversation_service = CheckinConversationService()
