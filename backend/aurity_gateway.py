"""
Free Intelligence - AURITY API Gateway

FastAPI gateway para integración AURITY ↔ FI.

Arquitectura:
  AURITY (Frontend React + Redux)
      ↓
  API Gateway (este módulo)
      ↓
  FI Backend (fi_consult_service + event_store + llm_router)

Endpoints:
  - POST /aurity/redux-action: Recibe Redux action, traduce a evento, persiste
  - GET /aurity/consultation/{id}: Reconstruye estado desde eventos
  - WebSocket /aurity/consultation/{id}/stream: Stream eventos en tiempo real

File: backend/aurity_gateway.py
Created: 2025-10-28
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from pathlib import Path

from backend.adapters_redux import ReduxAdapter, validate_redux_action
from backend.fi_event_store import EventStore
from backend.fi_consult_models import ConsultationEvent, Consultation
from backend.logger import get_logger

logger = get_logger(__name__)

# FastAPI app
app = FastAPI(
    title="AURITY ↔ FI Gateway",
    description="API Gateway para integración AURITY Frontend con Free Intelligence Backend",
    version="1.0.0"
)

# CORS (permite requests desde AURITY frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # AURITY dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redux adapter y event store
redux_adapter = ReduxAdapter()
event_store = EventStore(corpus_path="storage/corpus.h5")


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ReduxActionRequest(BaseModel):
    """Redux action from AURITY frontend"""
    type: str = Field(..., description="Redux action type (e.g., 'medicalChat/addMessage')")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Action payload")
    consultation_id: str = Field(..., description="Consultation ID")
    user_id: str = Field(default="aurity_user", description="User ID")


class ReduxActionResponse(BaseModel):
    """Response after processing Redux action"""
    success: bool
    event_id: str
    event_type: str
    consultation_id: str
    timestamp: str
    message: str


class ConsultationStateResponse(BaseModel):
    """Current consultation state reconstructed from events"""
    consultation_id: str
    state: Dict[str, Any]
    event_count: int
    last_updated: str


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    services: Dict[str, bool]


# ============================================================================
# WEBSOCKET CONNECTION MANAGER
# ============================================================================

class ConnectionManager:
    """Manage WebSocket connections for real-time event streaming"""

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, consultation_id: str):
        """Connect WebSocket for consultation"""
        await websocket.accept()
        if consultation_id not in self.active_connections:
            self.active_connections[consultation_id] = []
        self.active_connections[consultation_id].append(websocket)

        logger.info("WEBSOCKET_CONNECTED",
                   consultation_id=consultation_id,
                   total_connections=len(self.active_connections[consultation_id]))

    def disconnect(self, websocket: WebSocket, consultation_id: str):
        """Disconnect WebSocket"""
        if consultation_id in self.active_connections:
            self.active_connections[consultation_id].remove(websocket)
            if not self.active_connections[consultation_id]:
                del self.active_connections[consultation_id]

        logger.info("WEBSOCKET_DISCONNECTED", consultation_id=consultation_id)

    async def broadcast(self, consultation_id: str, message: Dict[str, Any]):
        """Broadcast message to all connected clients for consultation"""
        if consultation_id in self.active_connections:
            for connection in self.active_connections[consultation_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error("WEBSOCKET_BROADCAST_FAILED",
                               consultation_id=consultation_id,
                               error=str(e))


manager = ConnectionManager()


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        services={
            "event_store": True,  # TODO: Check HDF5 file exists
            "redux_adapter": True,
            "websocket_manager": True
        }
    )


@app.post("/aurity/redux-action", response_model=ReduxActionResponse)
async def process_redux_action(request: ReduxActionRequest):
    """
    Recibe Redux action de AURITY, traduce a domain event, persiste en event store.

    Flow:
      1. Validate Redux action structure
      2. Translate to domain event (via ReduxAdapter)
      3. Append to event store (HDF5 + SHA256)
      4. Broadcast to WebSocket subscribers (real-time updates)
      5. Return success response

    Example Redux action:
      {
        "type": "medicalChat/addMessage",
        "payload": {
          "role": "user",
          "content": "Patient has chest pain",
          "timestamp": "2025-10-28T12:00:00Z"
        },
        "consultation_id": "550e8400-e29b-41d4-a716-446655440000",
        "user_id": "aurity_user"
      }
    """
    logger.info("REDUX_ACTION_RECEIVED",
               action_type=request.type,
               consultation_id=request.consultation_id)

    try:
        # 1. Validate Redux action
        redux_action = {
            "type": request.type,
            "payload": request.payload
        }

        if not validate_redux_action(redux_action):
            raise HTTPException(
                status_code=400,
                detail="Invalid Redux action structure"
            )

        # 2. Translate to domain event
        event = redux_adapter.translate_action(
            redux_action=redux_action,
            consultation_id=request.consultation_id,
            user_id=request.user_id
        )

        # 3. Append to event store
        event_store.append_event(
            consultation_id=request.consultation_id,
            event=event
        )

        # 4. Broadcast to WebSocket subscribers
        await manager.broadcast(
            consultation_id=request.consultation_id,
            message={
                "type": "EVENT_APPENDED",
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "timestamp": event.timestamp.isoformat()
            }
        )

        logger.info("REDUX_ACTION_PROCESSED",
                   event_id=event.event_id,
                   event_type=event.event_type.value,
                   consultation_id=request.consultation_id)

        # 5. Return success
        return ReduxActionResponse(
            success=True,
            event_id=event.event_id,
            event_type=event.event_type.value,
            consultation_id=request.consultation_id,
            timestamp=event.timestamp.isoformat(),
            message=f"Redux action '{request.type}' processed successfully"
        )

    except Exception as e:
        logger.error("REDUX_ACTION_PROCESSING_FAILED",
                    action_type=request.type,
                    consultation_id=request.consultation_id,
                    error=str(e))

        raise HTTPException(
            status_code=500,
            detail=f"Failed to process Redux action: {str(e)}"
        )


@app.get("/aurity/consultation/{consultation_id}", response_model=ConsultationStateResponse)
async def get_consultation_state(consultation_id: str):
    """
    Reconstruye estado actual de consulta desde event stream.

    Flow:
      1. Load event stream from event store
      2. Reconstruct Consultation state from events
      3. Return current state

    Returns:
      - consultation_id: UUID
      - state: Current consultation state (messages, demographics, SOAP, etc.)
      - event_count: Total events in stream
      - last_updated: Timestamp of last event
    """
    logger.info("CONSULTATION_STATE_REQUESTED", consultation_id=consultation_id)

    try:
        # 1. Load events
        events = event_store.load_stream(consultation_id, verify_hashes=True)

        if not events:
            raise HTTPException(
                status_code=404,
                detail=f"Consultation {consultation_id} not found"
            )

        # 2. Reconstruct state
        consultation = Consultation(consultation_id=consultation_id)

        for event in events:
            # Apply event to consultation state
            # (Consultation model should have apply_event method)
            pass  # TODO: Implement state reconstruction logic

        # 3. Return state
        return ConsultationStateResponse(
            consultation_id=consultation_id,
            state=consultation.dict(),
            event_count=len(events),
            last_updated=events[-1].timestamp.isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("CONSULTATION_STATE_RECONSTRUCTION_FAILED",
                    consultation_id=consultation_id,
                    error=str(e))

        raise HTTPException(
            status_code=500,
            detail=f"Failed to reconstruct consultation state: {str(e)}"
        )


@app.websocket("/aurity/consultation/{consultation_id}/stream")
async def websocket_event_stream(websocket: WebSocket, consultation_id: str):
    """
    WebSocket para streaming de eventos en tiempo real.

    Flow:
      1. Client connects
      2. Server sends historical events (catchup)
      3. Server streams new events as they arrive
      4. Client disconnects

    Example client code (JavaScript):
      const ws = new WebSocket('ws://localhost:7002/aurity/consultation/{id}/stream');
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Event received:', data);
      };
    """
    await manager.connect(websocket, consultation_id)

    try:
        # Send historical events (catchup)
        try:
            events = event_store.load_stream(consultation_id, verify_hashes=False)
            for event in events:
                await websocket.send_json({
                    "type": "HISTORICAL_EVENT",
                    "event_id": event.event_id,
                    "event_type": event.event_type.value,
                    "timestamp": event.timestamp.isoformat(),
                    "payload": event.payload
                })
        except Exception as e:
            logger.error("WEBSOCKET_CATCHUP_FAILED",
                        consultation_id=consultation_id,
                        error=str(e))

        # Keep connection alive and wait for new events
        while True:
            # Wait for client messages (ping/pong)
            data = await websocket.receive_text()

            # Echo back (ping/pong)
            await websocket.send_json({
                "type": "PONG",
                "timestamp": datetime.utcnow().isoformat()
            })

    except WebSocketDisconnect:
        manager.disconnect(websocket, consultation_id)
        logger.info("WEBSOCKET_CLIENT_DISCONNECTED", consultation_id=consultation_id)


# ============================================================================
# CLI / STANDALONE SERVER
# ============================================================================

def main():
    """Run AURITY Gateway standalone"""
    import uvicorn

    print("\n" + "="*70)
    print("🚀 AURITY ↔ FI API Gateway")
    print("="*70)
    print("\nEndpoints:")
    print("  - GET /health")
    print("  - POST /aurity/redux-action")
    print("  - GET /aurity/consultation/{id}")
    print("  - WebSocket /aurity/consultation/{id}/stream")
    print(f"\nServer starting on http://localhost:7002")
    print("="*70 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=7002)


if __name__ == "__main__":
    main()
