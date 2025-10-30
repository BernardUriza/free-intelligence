# Integración Aurity Framework ↔ FI FastAPI

> **Sprint SPR-2025W44** - Puntos de integración con el backend FI
> **Status**: Ready for Integration
> **Fecha**: 2025-10-28

## Estado Actual

### ✅ Aurity Framework (Frontend + Orchestration)

- **Staging**: `http://localhost:3001` ✅ Operacional
- **Triage Intake**: `/triage` - Formulario de captura ✅
- **API Endpoints**:
  - `/api/health` ✅ Funcionando
  - `/api/triage/intake` ✅ Preparado
  - `/api/triage/transcribe` ✅ Preparado

### 🚀 FI FastAPI (Backend Core) - En Desarrollo

**Endpoints esperados del FI:**

```python
# Base URL (ejemplo)
FI_API_BASE = "http://localhost:8000"

# Endpoints que necesitamos:
POST /fi/triage/intake          # Recibir datos de triage
POST /fi/triage/transcribe      # Transcripción de audio vía Whisper
GET  /fi/health                 # Health check
POST /fi/storage/store          # Almacenar buffers
GET  /fi/storage/retrieve/{id}  # Recuperar buffers
POST /fi/auth/login             # Autenticación
GET  /fi/auth/verify            # Verificar token
```

## Arquitectura de Integración

```
┌─────────────────────────────────────────────────────────────────┐
│                     AURITY FRAMEWORK                            │
│                  (Next.js 14 - Orchestrator)                    │
│                                                                 │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐ │
│  │   Triage     │      │  Conversation│      │   Storage    │ │
│  │   Intake     │      │   Capture    │      │   Manager    │ │
│  │   UI         │      │              │      │              │ │
│  └──────┬───────┘      └──────┬───────┘      └──────┬───────┘ │
│         │                     │                     │         │
│         └─────────────┬───────┴─────────────────────┘         │
│                       │                                       │
│                       ▼                                       │
│              ┌─────────────────┐                             │
│              │  API Routes     │                             │
│              │  (Next.js API)  │                             │
│              └────────┬────────┘                             │
└───────────────────────┼──────────────────────────────────────┘
                        │
                        │ HTTP/REST
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FI FASTAPI BACKEND                           │
│                  (Core Business Logic)                          │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │   Triage     │  │   Storage    │  │     Auth     │        │
│  │   Service    │  │   Service    │  │   Service    │        │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘        │
│         │                 │                 │                 │
│         └────────┬────────┴────────┬────────┘                 │
│                  │                 │                          │
│                  ▼                 ▼                          │
│         ┌─────────────────┐ ┌──────────────┐                 │
│         │   PostgreSQL    │ │    Redis     │                 │
│         └─────────────────┘ └──────────────┘                 │
└─────────────────────────────────────────────────────────────────┘
```

## Variables de Entorno Necesarias

### Aurity Framework (`.env.staging`)

```bash
# FI FastAPI Backend URL
FI_API_URL=http://localhost:8000
FI_API_TIMEOUT=30000

# Credenciales de servicio (Aurity → FI)
FI_SERVICE_USER=aurity-service
FI_SERVICE_TOKEN=${FI_SERVICE_TOKEN}

# Existing config...
WHISPER_API_KEY=${WHISPER_API_KEY}
OPENAI_API_KEY=${OPENAI_API_KEY}
JWT_SECRET=${JWT_SECRET}
```

### FI FastAPI (`.env`)

```bash
# Database
DATABASE_URL=postgresql://fi_staging:password@localhost:5432/aurity_staging

# Redis
REDIS_URL=redis://:staging-redis-change-me@localhost:6379

# Storage
STORAGE_BASE_DIR=/tmp/fi-storage
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=staging-minio-access
MINIO_SECRET_KEY=staging-minio-secret-change-me

# Auth
JWT_SECRET=${JWT_SECRET}
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

# External APIs
WHISPER_API_KEY=${WHISPER_API_KEY}
OPENAI_API_KEY=${OPENAI_API_KEY}

# CORS (permitir Aurity)
CORS_ORIGINS=http://localhost:3001,http://localhost:3000

# Environment
ENV=staging
```

## Flujo de Integración: Triage Intake

### 1. Usuario completa formulario en Aurity

```typescript
// app/triage/page.tsx
const handleSubmit = async (data: TriageData) => {
  // Aurity envía a su propio API endpoint
  const response = await fetch('/api/triage/intake', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(data)
  });
};
```

### 2. Aurity API reenvía a FI FastAPI

```typescript
// app/api/triage/intake/route.ts (ACTUALIZAR)
export async function POST(request: NextRequest) {
  // Validar token de Aurity
  const token = request.headers.get('authorization');
  const validation = authManager.verifyToken(token);

  if (!validation.valid) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  // Obtener datos del request
  const data = await request.json();

  // ⚠️ NUEVO: Reenviar a FI FastAPI
  const fiResponse = await fetch(`${process.env.FI_API_URL}/fi/triage/intake`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${process.env.FI_SERVICE_TOKEN}`,
      'X-Aurity-Session': validation.payload.sessionId
    },
    body: JSON.stringify(data)
  });

  if (!fiResponse.ok) {
    return NextResponse.json(
      { error: 'FI API error', details: await fiResponse.text() },
      { status: fiResponse.status }
    );
  }

  const fiData = await fiResponse.json();

  // Opcional: Almacenar en storage local de Aurity
  const storage = getStorageManager();
  await storage.storeBuffer(
    BufferType.TRIAGE_DATA,
    Buffer.from(JSON.stringify(data)),
    {
      source: 'triage-intake',
      timestamp: Date.now(),
      size: 0,
      tags: ['triage', 'fi-synced']
    }
  );

  return NextResponse.json({
    success: true,
    fiResponse: fiData
  });
}
```

### 3. FI FastAPI procesa y responde

```python
# fi_api/routers/triage.py
from fastapi import APIRouter, Depends, HTTPException
from fi_api.services.triage_service import TriageService
from fi_api.auth.dependencies import get_current_user

router = APIRouter(prefix="/fi/triage", tags=["triage"])

@router.post("/intake")
async def create_triage_intake(
    data: TriageIntakeData,
    current_user: User = Depends(get_current_user),
    service: TriageService = Depends()
):
    """
    Recibe datos de triage desde Aurity Framework
    """
    try:
        # Validar datos
        validated_data = await service.validate_triage_data(data)

        # Almacenar en PostgreSQL
        triage_record = await service.create_triage_record(validated_data)

        # Almacenar buffer en MinIO/Storage
        buffer_id = await service.store_triage_buffer(triage_record)

        # Indexar en Meilisearch para búsqueda
        await service.index_triage(triage_record)

        return {
            "success": True,
            "triage_id": triage_record.id,
            "buffer_id": buffer_id,
            "timestamp": triage_record.created_at
        }

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
```

## Flujo de Integración: Audio Transcription

### 1. Usuario graba audio en Aurity

```typescript
// app/api/triage/transcribe/route.ts (ACTUALIZAR)
export async function POST(request: NextRequest) {
  const formData = await request.formData();
  const audioFile = formData.get('audio') as File;

  // Validar token
  const token = request.headers.get('authorization');
  const validation = authManager.verifyToken(token);

  if (!validation.valid) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  // ⚠️ NUEVO: Reenviar a FI FastAPI
  const fiFormData = new FormData();
  fiFormData.append('audio', audioFile);
  fiFormData.append('language', 'es');

  const fiResponse = await fetch(`${process.env.FI_API_URL}/fi/triage/transcribe`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${process.env.FI_SERVICE_TOKEN}`,
    },
    body: fiFormData
  });

  if (!fiResponse.ok) {
    return NextResponse.json(
      { error: 'Transcription failed' },
      { status: fiResponse.status }
    );
  }

  const transcription = await fiResponse.json();

  return NextResponse.json({
    success: true,
    text: transcription.text,
    duration: transcription.duration
  });
}
```

### 2. FI FastAPI llama a Whisper

```python
# fi_api/routers/triage.py
from fi_api.services.whisper_service import WhisperService

@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = "es",
    current_user: User = Depends(get_current_user),
    whisper_service: WhisperService = Depends()
):
    """
    Transcribe audio usando OpenAI Whisper
    """
    try:
        # Guardar temporalmente
        temp_path = await save_upload_file(audio)

        # Transcribir con Whisper
        transcription = await whisper_service.transcribe(
            audio_path=temp_path,
            language=language
        )

        # Limpiar archivo temporal
        os.unlink(temp_path)

        return {
            "success": True,
            "text": transcription.text,
            "duration": transcription.duration,
            "language": transcription.language
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## Autenticación entre Servicios

### Service-to-Service Auth

```python
# fi_api/auth/dependencies.py
from fastapi import Header, HTTPException

async def verify_service_token(
    authorization: str = Header(None)
) -> dict:
    """
    Verifica que el request viene de Aurity Framework
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization")

    try:
        token = authorization.replace("Bearer ", "")

        # Verificar JWT
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )

        # Verificar que es un service token
        if payload.get("type") != "service":
            raise HTTPException(status_code=403, detail="Invalid token type")

        return payload

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

## Checklist de Integración

### Pre-requisitos

- [ ] FI FastAPI corriendo en `http://localhost:8000`
- [ ] FI API responde a `/health` endpoint
- [ ] PostgreSQL compartido entre Aurity y FI
- [ ] Redis accesible desde ambos servicios
- [ ] MinIO configurado y accesible

### Aurity Side

- [ ] Agregar `FI_API_URL` a `.env.staging`
- [ ] Generar `FI_SERVICE_TOKEN` para auth
- [ ] Actualizar `/api/triage/intake/route.ts`
- [ ] Actualizar `/api/triage/transcribe/route.ts`
- [ ] Agregar error handling para FI API calls
- [ ] Agregar retry logic (opcional)

### FI FastAPI Side

- [ ] Implementar `/fi/triage/intake` endpoint
- [ ] Implementar `/fi/triage/transcribe` endpoint
- [ ] Implementar `/fi/health` endpoint
- [ ] Agregar CORS para `http://localhost:3001`
- [ ] Configurar JWT verification
- [ ] Conectar a PostgreSQL compartido
- [ ] Conectar a Redis compartido
- [ ] Configurar Whisper API

### Testing

- [ ] Test health checks (Aurity → FI)
- [ ] Test triage intake flow end-to-end
- [ ] Test audio transcription flow
- [ ] Test error handling
- [ ] Test auth (válido/inválido)
- [ ] Performance test (latency)

## Comandos Útiles

### Iniciar ambos servicios

```bash
# Terminal 1: Aurity Staging
docker-compose -f docker-compose.staging.yml up -d
# App en http://localhost:3001

# Terminal 2: FI FastAPI
cd /path/to/fi-api
uvicorn main:app --reload --port 8000
# API en http://localhost:8000
```

### Test de integración

```bash
# 1. Health check FI
curl http://localhost:8000/fi/health

# 2. Health check Aurity
curl http://localhost:3001/api/health

# 3. Test triage desde Aurity (que llama a FI)
curl -X POST http://localhost:3001/api/triage/intake \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "patientName": "Test Patient",
    "chiefComplaint": "Dolor de cabeza",
    "symptoms": ["dolor", "náusea"],
    "severity": "moderate"
  }'
```

## Próximos Pasos

1. **Implementar endpoints FI FastAPI**
2. **Actualizar Aurity API routes** para llamar a FI
3. **Configurar auth service-to-service**
4. **Testing de integración**
5. **Documentar APIs con OpenAPI/Swagger**

---

**Fecha**: 2025-10-28
**Sprint**: SPR-2025W44
**Status**: Ready for FI FastAPI Integration
**Version**: 0.1.0
