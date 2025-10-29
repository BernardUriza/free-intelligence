# AURITY FRAMEWORK
## Low-Level Design Document v1.0
### Artificial United Robust Intelligence for Telemedicine Yield

---

## EXECUTIVE SUMMARY

Aurity es un framework de telemedicina edge-first que integra Free Intelligence (FI) como sistema nervioso técnico local, proporcionando memoria clínica verificable sin dependencia de nubes opacas. Diseñado para clínicas privadas LATAM con infraestructura robusta (NAS on-premise, conectividad estable), Aurity opera bajo el principio de soberanía de datos: la información sensible nunca sale del perímetro controlado por el médico.

**Arquitectura core:** ESP32 wearable → Celular → NAS (Free Intelligence) → Servicios opcionales cloud
**Filosofía:** On-premise first, cloud when necessary, HIPAA-compliant by design
**Target:** Clínicas 2-10 médicos con inversión en infraestructura tecnológica

---

## 1. ROADMAP FI-HEALTH: ESTRATEGIA DE ENTRADA AL MERCADO

### 1.1 Visión General

FI-Health adopta estrategia de **no-PHI-first** para generar ingresos tempranos mientras construye certificaciones regulatorias. El roadmap se estructura en 4 fases progresivas, cada una con ROI independiente.

### 1.2 Fase 1 – Infraestructuras Seguras sin PHI (Meses 1-4)

**Objetivo:** Demostrar valor sin tocar datos clínicos sensibles.

**Módulos:**

**FI-Cold (Cadena de Frío Biomédica)**
- Monitoreo continuo temperatura/humedad en refrigeradores vacunas/medicamentos
- Sensores IoT (ESP32 + DHT22) conectados a NAS vía MQTT
- Alertas automáticas si temperatura fuera de rango (2-8°C vacunas)
- Reportes de cumplimiento NOM-SSA para auditorías sanitarias
- **Revenue:** $50-80 USD/mes por clínica (compliance obligatorio)

**FI-Entry (Control de Accesos Físicos)**
- Cámaras con blurring automático de rostros (privacidad por defecto)
- Detección de intrusiones fuera de horario
- Registro de eventos (apertura/cierre, movimiento detectado)
- Integración con cerraduras inteligentes existentes
- **Revenue:** $30-50 USD/mes por sede

**Características técnicas:**
```yaml
Hardware:
  - Sensores temperatura: DS18B20 / DHT22
  - Cámaras: IP con ONVIF + edge processing
  - Gateway: ESP32 con MQTT client

Software:
  - FI ingestion: MQTT broker en NAS
  - Storage: TimescaleDB para series temporales
  - Alerting: Webhook a WhatsApp Business API
  - Dashboard: Grafana embedded en NAS

Compliance:
  - Sin PHI: 0% riesgo regulatorio
  - Logs inmutables con SHA256
  - Reportes automáticos para SSA
```

**ROI clínica:** Break-even en 3 meses (vs multas por cadena de frío rota: $5,000+ USD)

### 1.3 Fase 2 – Gestión Documental No Clínica (Meses 5-8)

**Objetivo:** Digitalizar trazabilidad técnica de equipos biomédicos.

**Módulos:**

**FI-Assets (Inventario Biomédico)**
- Registro digital de equipos (autoclave, ECG, ultrasonido)
- Calendario mantenimiento preventivo con alertas
- Escaneo QR para consulta rápida de manuales/historial
- **Revenue:** $40 USD/mes por clínica

**FI-Calibration (Calibraciones y Metrología)**
- Digitalización de certificados de calibración (PDF → hash + metadata)
- Vencimientos y renovaciones automáticas
- Exportación de trazas para auditorías ISO 9001
- **Revenue:** $35 USD/mes por clínica

**FI-Logistics (Insumos y Compras)**
- Inventario de consumibles (guantes, jeringas, suero)
- Alertas de reorden automático
- Integración con distribuidores médicos (API o email)
- **Revenue:** $25 USD/mes por clínica

**Características técnicas:**
```yaml
Ingestion:
  - PDF upload vía web interface
  - Extracción metadata con Tesseract OCR
  - Clasificación automática (calibración/manual/factura)

Storage:
  - PostgreSQL para metadata estructurada
  - MinIO para PDFs originales
  - SHA256 hash chain por documento

Features:
  - Búsqueda full-text con Meilisearch
  - Timeline navegable por equipo
  - Exportación Excel/PDF para auditorías
```

**ROI clínica:** $100 USD/mes por módulo vs $500+ USD/año en multas por documentación incompleta

### 1.4 Fase 3 – FI-Core On-Prem: Procesamiento Local de PHI (Meses 9-14)

**Objetivo:** Habilitar procesamiento de datos clínicos sensibles **sin que salgan del NAS**.

**Arquitectura FI-Core:**

```
┌─────────────────────────────────────────────┐
│            NAS Synology DS923+              │
│  ┌───────────────────────────────────────┐  │
│  │         Free Intelligence Core        │  │
│  │  ┌─────────────────────────────────┐  │  │
│  │  │   Ingestion Layer               │  │  │
│  │  │  - Audio/Video segmentation     │  │  │
│  │  │  - PDF/DICOM parsing            │  │  │
│  │  │  - HL7/FHIR file ingestion      │  │  │
│  │  └─────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────┐  │  │
│  │  │   Validation Layer              │  │  │
│  │  │  - SHA256 per segment           │  │  │
│  │  │  - Manifest generation          │  │  │
│  │  │  - Consent verification         │  │  │
│  │  └─────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────┐  │  │
│  │  │   Processing Layer (Optional)   │  │  │
│  │  │  - Susurro VAD + transcription  │  │  │
│  │  │  - Redaction/pseudonymization   │  │  │
│  │  │  - Qdrant semantic search       │  │  │
│  │  └─────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────┐  │  │
│  │  │   Governance Layer              │  │  │
│  │  │  - RBAC (owner/médico/auditor)  │  │  │
│  │  │  - Retention policies           │  │  │
│  │  │  - Audit logs (WORM)            │  │  │
│  │  │  - Legal hold management        │  │  │
│  │  └─────────────────────────────────┘  │  │
│  └───────────────────────────────────────┘  │
│  ┌───────────────────────────────────────┐  │
│  │         Storage Layer                 │  │
│  │  - PostgreSQL (metadata + structure)  │  │
│  │  - MinIO (objects: audio/video/PDF)   │  │
│  │  - Qdrant (embeddings)                │  │
│  │  - TimescaleDB (metrics/logs)         │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

**FI-Tele: Teleconsulta con Memoria Técnica**

Flujo de sesión:
```
1. Doctor inicia consulta → FI crea episodio con UUID
2. Audio/video streamed en segmentos 60-120s
3. Por cada segmento:
   - SHA256 calculado en tiempo real
   - Metadata: timestamp, participante, canal
   - Consentimiento verificado (firma digital previa)
4. Susurro (VAD) detecta voz activa:
   - Transcribe solo segmentos con habla (ahorra 60% proceso)
   - Genera marcadores: "síntomas", "diagnóstico", "plan"
5. Fin de sesión:
   - Manifest completo con todos los hashes
   - Timeline navegable para review
   - Exportación segura si autorizada (PDF firmado)
```

**Características técnicas:**
```yaml
Ingestion:
  - WebRTC → RTMP → ffmpeg segmentation
  - Audio: 16kHz mono, segmentos 90s (Whisper optimal)
  - Video: 720p H.264, blurred faces optional

VAD (Voice Activity Detection):
  - Silero VAD local (torch inference)
  - Threshold: -40dB, window 1.5s
  - Reduce transcription cost 60-70%

Transcription:
  - Whisper large-v3 local (Docker + GPU)
  - Latency: <3s por segmento
  - Accuracy target: >92% español médico

Hashing:
  - SHA256 por segmento + manifest global
  - Firmado con clave privada clínica (PKI)
  - Verificación en auditoría con clave pública

Storage:
  - Raw segments: MinIO (immutable)
  - Transcripts: PostgreSQL con full-text search
  - Manifests: JSON + WORM flag
```

**FI-Records: Expediente Clínico Complementario**

No reemplaza al HIS/EHR existente, lo aumenta:

```
HIS/EHR (Sistema principal)
    ↕ API/SFTP
FI-Records (Capa de verdad técnica)
    ↓
- Ingesta documentos (PDF, DICOM, HL7)
- Extracción metadata automática
- Timeline por paciente/episodio
- Hashes inmutables para evidencia legal
```

**Tipos de documentos soportados:**

```yaml
Clinical:
  - Recetas (PDF/JSON versionadas)
  - Laboratorios (PDF + structured observables)
  - Radiología (DICOM + reports)
  - Notas de evolución (transcripts + structured)

Administrative:
  - Consentimientos informados
  - Autorizaciones de seguros
  - Facturas y comprobantes

Technical:
  - Órdenes médicas
  - Interconsultas
  - Reportes de enfermería
```

**Recetas electrónicas con FI:**
```json
{
  "receta_id": "RX-2025-001234",
  "version": 2,
  "previous_version_hash": "a3f5...",
  "timestamp": "2025-10-25T14:32:00Z",
  "doctor": {
    "cedula": "123456",
    "firma_digital": "PEM cert SHA256"
  },
  "patient_pseudonym": "PAT-xK4j9",
  "medications": [
    {
      "nombre": "Metformina",
      "dosis": "850mg",
      "frecuencia": "cada 12 horas",
      "duracion": "30 días"
    }
  ],
  "hash_sha256": "b7e3...",
  "immutable": true,
  "legal_hold": false
}
```

Cada enmienda crea nuevo objeto con vínculo al anterior (blockchain local).

**Laboratorios estructurados:**
```json
{
  "lab_id": "LAB-2025-005678",
  "tipo": "Química sanguínea",
  "fecha_muestra": "2025-10-24T08:00:00Z",
  "observaciones": [
    {
      "analito": "Glucosa",
      "valor": 126,
      "unidad": "mg/dL",
      "rango_referencia": "70-100",
      "critico": false
    },
    {
      "analito": "Potasio",
      "valor": 6.2,
      "unidad": "mEq/L",
      "rango_referencia": "3.5-5.0",
      "critico": true,
      "alerta_generada": true
    }
  ],
  "pdf_original_hash": "c9d2...",
  "laboratorio_externo": "LabCorp México"
}
```

Búsqueda: "potasio crítico últimos 30 días" → resultados inmediatos + PDF verificado

**Governance y Compliance:**

```yaml
RBAC:
  owner:
    - Full access
    - Gestión usuarios y políticas
  compliance_officer:
    - Auditoría completa
    - Exportación evidencias
    - No modifica datos clínicos
  medico:
    - Lee/escribe expedientes asignados
    - No borra, solo crea versiones
  auditor_externo:
    - Solo lectura con bitácora
    - Acceso temporal (token expira)

Retention:
  operational: 30-90 días (consultas rutinarias)
  evidence: 5-7 años (disputas, auditorías SSA)
  legal_hold: indefinido hasta release manual

Audit:
  - Cada acceso loggea: quién, qué, cuándo, desde dónde
  - Exports registran: documento, destino, justificación
  - WORM log (append-only, no delete)

SLO/SLI:
  - Uptime: >99.5% mensual
  - Latency ingestion: p95 <2s
  - Search response: p99 <500ms
  - Backup success: 100% daily
```

**Semantic Search con Qdrant:**

```python
# Embedding local con sentence-transformers
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')
qdrant = QdrantClient(host='localhost', port=6333)

# Index nota clínica
nota = "Paciente masculino 45 años, diabético tipo 2, descompensado..."
embedding = model.encode(nota)

qdrant.upsert(
    collection_name="notas_clinicas",
    points=[{
        "id": nota_id,
        "vector": embedding.tolist(),
        "payload": {
            "paciente_id": "PAT-xK4j9",
            "fecha": "2025-10-25",
            "tipo": "evolucion",
            "hash": "d4f6..."
        }
    }]
)

# Query semántica
query = "pacientes con diabetes descontrolada"
results = qdrant.search(
    collection_name="notas_clinicas",
    query_vector=model.encode(query).tolist(),
    limit=10
)
```

Resultados relevantes sin SQL, con verificación hash por documento.

**Revenue Fase 3:**
- FI-Core license: $200 USD/mes por clínica
- Setup fee: $500 USD one-time
- Whisper GPU upgrade (optional): $150 USD/mes

**ROI clínica:**
- Ahorro auditorías: -80% tiempo búsqueda documentos
- Prevención disputas legales: evidencia verificable invaluable
- Reducción vendor-lock-in: control total de datos

### 1.5 Fase 4 – Servicios Clínicos Regulados (Meses 15-24)

**Objetivo:** Certificaciones ISO 27001 + cumplimiento NOM-SSA para ofrecer servicios completamente integrados.

**Pre-requisitos:**
- ISO 27001:2022 (seguridad información)
- NOM-024-SSA3-2012 (expediente clínico electrónico)
- COFEPRIS registro software médico Clase I/II
- Certificación HL7/FHIR interoperability

**Módulos regulados:**

**FI-Tele Pro (Teleconsulta Certificada)**
- Integración con plataformas de videollamada certificadas
- Firma electrónica avanzada (e.firma SAT)
- Receta electrónica con validación COFEPRIS
- Interoperabilidad con farmacias (QR verificable)

**FI-Lab Connect (Integración Laboratorios)**
- Conectores HL7 v2.5 para laboratorios externos
- Ingesta automática de resultados
- Alertas críticas en tiempo real
- Dashboard tendencias por paciente

**FI-FHIR Gateway (Interoperabilidad Nacional)**
- Servidor FHIR R4 compatible
- Exportación segura a sistemas SSA
- Federación entre clínicas (metadata only)
- Anonimización para estudios epidemiológicos

**Revenue Fase 4:**
- FI-Tele Pro: $150 USD/mes + $2 USD/consulta
- FI-Lab Connect: $100 USD/mes + integración lab
- FI-FHIR Gateway: $250 USD/mes (enterprise)

**Timeline certificaciones:**
- ISO 27001: 8-12 meses ($15,000-25,000 USD)
- NOM-024-SSA3: 6-9 meses ($8,000-12,000 USD)
- COFEPRIS: 4-6 meses ($5,000-8,000 USD)
- **Total inversión:** ~$30,000-45,000 USD
- **Financiado por:** Revenue Fases 1-2-3

---

## 2. FREE INTELLIGENCE: SISTEMA NERVIOSO TÉCNICO

### 2.1 Arquitectura Conceptual

Free Intelligence es el motor que convierte archivos dispersos en **memoria clínica verificable**. Opera como "caja negra benigna" que:

1. **Captura** todo insumo clínico con integridad
2. **Valida** mediante hashing criptográfico
3. **Resume** con políticas claras (opt-in)
4. **Gobierna** accesos y retenciones

### 2.2 Componentes Core

**Ingestion Layer: Captura Multi-Formato**

```yaml
Audio/Video:
  - Segmentación automática 60-120s
  - Codecs soportados: H.264, AAC, Opus
  - Manifest metadata: timestamp, speaker, channel

Documentos:
  - PDF: Tesseract OCR + metadata extraction
  - DICOM: pydicom parsing + anonymization
  - HL7/FHIR: HAPI validator + transformation

IoT Streams:
  - MQTT broker interno
  - Time-series compression (TimescaleDB)
  - Alerting rules engine
```

**Validation Layer: Integridad Criptográfica**

```python
# Por cada segmento/documento
def compute_integrity_hash(content: bytes) -> str:
    """SHA256 determinístico"""
    return hashlib.sha256(content).hexdigest()

def create_manifest(segments: List[Segment]) -> Manifest:
    """Manifest con firma digital"""
    manifest = {
        "version": "1.0",
        "session_id": uuid4(),
        "timestamp": datetime.utcnow().isoformat(),
        "segments": [
            {
                "id": seg.id,
                "hash": compute_integrity_hash(seg.data),
                "duration": seg.duration,
                "speaker": seg.speaker,
                "consent": seg.consent_verified
            }
            for seg in segments
        ]
    }

    # Firma con clave privada clínica
    manifest["signature"] = sign_with_private_key(
        json.dumps(manifest, sort_keys=True),
        clinic_private_key
    )

    return manifest
```

**Processing Layer: Políticas Opt-In**

```yaml
Susurro Module (VAD + Transcription):
  trigger: explicit_policy_per_session
  modes:
    - disabled: solo storage, 0 processing
    - vad_only: detección voz, sin transcripción
    - transcribe_full: VAD + Whisper local
    - summarize: transcripción + Claude markers

  consent_required: true
  data_residency: never_leaves_nas
  output_encryption: AES-256-GCM

Redaction Engine:
  triggers:
    - external_export
    - federated_sharing
    - research_datasets

  methods:
    - regex_patterns: (RFC, CURP, tel, email)
    - NER_model: spaCy es_core_news_lg
    - manual_review: UI para validar

  audit: every_redaction_logged
```

**Governance Layer: RBAC + Retention**

```sql
-- RBAC Schema
CREATE TABLE roles (
    id UUID PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    permissions JSONB NOT NULL
);

CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    role_id UUID REFERENCES roles(id),
    clinic_id UUID REFERENCES clinics(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Audit Log (WORM)
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID NOT NULL,
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    success BOOLEAN NOT NULL,
    error_message TEXT
);

-- Prohibir deletes en audit_log
CREATE RULE no_delete_audit AS ON DELETE TO audit_log DO INSTEAD NOTHING;
CREATE RULE no_update_audit AS ON UPDATE TO audit_log DO INSTEAD NOTHING;

-- Retention Policies
CREATE TABLE retention_policies (
    id UUID PRIMARY KEY,
    resource_type VARCHAR(50) NOT NULL,
    category VARCHAR(50) NOT NULL, -- operational, evidence, legal_hold
    retention_days INT NOT NULL,
    auto_delete BOOLEAN DEFAULT false,
    clinic_id UUID REFERENCES clinics(id)
);

-- Legal Hold
CREATE TABLE legal_holds (
    id UUID PRIMARY KEY,
    resource_id UUID NOT NULL,
    reason TEXT NOT NULL,
    applied_by UUID REFERENCES users(id),
    applied_at TIMESTAMPTZ DEFAULT NOW(),
    released_at TIMESTAMPTZ,
    released_by UUID REFERENCES users(id)
);
```

### 2.3 Storage Architecture

**Multi-Tier Storage en NAS:**

```
┌─────────────────────────────────────────┐
│  Hot Storage (SSD Cache)                │
│  - Últimos 7 días                       │
│  - Búsquedas frecuentes                 │
│  - Metadata siempre                     │
│  Latency: <100ms                        │
└─────────────────────────────────────────┘
            ↓ aging
┌─────────────────────────────────────────┐
│  Warm Storage (HDD RAID6)               │
│  - 8-90 días                            │
│  - Documentos operacionales             │
│  - Audio/video consultados              │
│  Latency: <2s                           │
└─────────────────────────────────────────┘
            ↓ archival
┌─────────────────────────────────────────┐
│  Cold Storage (Compressed)              │
│  - >90 días                             │
│  - Evidencias legales                   │
│  - Backups históricos                   │
│  Latency: <30s                          │
└─────────────────────────────────────────┘
```

**Backup Strategy:**

```yaml
Local:
  - Btrfs snapshots: cada 6 horas, retención 7 días
  - Full backup: diario a 2am, retención 30 días
  - Incremental: cada hora, retención 24 horas

Offsite:
  - NAS secundario (opcional): replicación continua
  - Cloud encrypted: Backblaze B2, solo metadata + hashes
  - Recovery Time Objective (RTO): <4 horas
  - Recovery Point Objective (RPO): <1 hora
```

### 2.4 Búsqueda y Analytics

**Triple Index Strategy:**

```yaml
PostgreSQL Full-Text:
  - Metadata estructurada
  - Campos categóricos
  - Query: "recetas metformina octubre"
  Performance: <50ms

Meilisearch:
  - Texto completo documentos
  - Typo tolerance
  - Query: "paciente hipertenso descontolado"
  Performance: <200ms

Qdrant Semantic:
  - Búsqueda conceptual
  - Query: "casos similares diabetes complicada"
  Performance: <500ms
```

**Unified Search API:**

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class SearchRequest(BaseModel):
    query: str
    filters: dict = {}
    mode: str = "hybrid"  # structured | fulltext | semantic | hybrid

@app.post("/search")
async def unified_search(req: SearchRequest):
    """Búsqueda multi-índice con ranking fusion"""

    results = []

    if req.mode in ["structured", "hybrid"]:
        # PostgreSQL para campos exactos
        pg_results = await search_postgres(req.query, req.filters)
        results.extend(pg_results)

    if req.mode in ["fulltext", "hybrid"]:
        # Meilisearch para texto completo
        ms_results = await search_meilisearch(req.query, req.filters)
        results.extend(ms_results)

    if req.mode in ["semantic", "hybrid"]:
        # Qdrant para búsqueda conceptual
        qd_results = await search_qdrant(req.query, req.filters)
        results.extend(qd_results)

    # Reciprocal Rank Fusion
    final_results = reciprocal_rank_fusion(results)

    # Verificar hashes para cada resultado
    for result in final_results:
        result["integrity_verified"] = verify_hash(result["id"])

    return final_results
```

---

## 3. HARDWARE SPECIFICATIONS

### 3.1 NAS Requirements

**Tier 1: Clínicas 2-5 Médicos**
```yaml
Model: Synology DS923+
CPU: AMD Ryzen R1600 dual-core 2.6GHz
RAM: 32GB DDR4 ECC (upgrade from 4GB)
Bays: 4x 3.5" SATA
Drives: 4x 4TB WD Red Plus (RAID6 = 8TB usable)
Network: 2x 1GbE (bonding)
Cache: 2x 500GB M.2 NVMe SSD
UPS: APC Smart-UPS 1500VA
Cost: ~$2,500 USD total

Capacity:
- 8TB usable = ~20,000 horas audio
- ~4,000 sesiones teleconsulta completas
- ~200,000 documentos PDF
```

**Tier 2: Clínicas 6-10 Médicos**
```yaml
Model: Synology RS2423+
CPU: AMD Ryzen V1500B quad-core 2.2GHz
RAM: 64GB DDR4 ECC
Bays: 12x 3.5" SATA
Drives: 8x 8TB WD Red Pro (RAID6 = 48TB usable)
Network: 4x 1GbE + 10GbE upgrade
Cache: 2x 1TB M.2 NVMe SSD
UPS: APC Smart-UPS 3000VA
Cost: ~$8,000 USD total

Capacity:
- 48TB usable = ~120,000 horas audio
- ~24,000 sesiones teleconsulta
- ~1,200,000 documentos PDF
```

### 3.2 Wearable Audio Capture

**ESP32-C3 Custom Pendant:**
```yaml
MCU: ESP32-C3-MINI-1 (160MHz, 400KB SRAM)
Audio: INMP441 I2S MEMS Mic (-26dB sensitivity)
Bluetooth: BLE 5.0, A2DP profile
Battery: LiPo 402030 300mAh (8h streaming)
Charging: USB-C, TP4056 module
Case: PETG 3D printed, 22x28x9mm
Activation: Reed switch + magnetic ring
Weight: <15 gramos
Cost per unit: $20 USD

Firmware:
- Audio sample: 16kHz mono, 16-bit
- Streaming: Bluetooth A2DP to mobile
- Power: Deep sleep <1µA, active 80mA
- Range: 10 metros line-of-sight
```

### 3.3 Network Infrastructure

**Minimum Requirements:**
```yaml
Internet:
  - Downlink: 50 Mbps (fiber optic preferred)
  - Uplink: 10 Mbps
  - Latency: <50ms
  - Provider: Business tier with SLA

LAN:
  - Switch: Managed Gigabit 24-port
  - WiFi: WiFi 6 (802.11ax) dual-band
  - Access Points: 2+ Ubiquiti UniFi UAP
  - Cabling: Cat6 throughout facility
  - VLAN: Separate clinical/admin/guest

Security:
  - Firewall: pfSense/OPNsense appliance
  - VPN: WireGuard for remote access
  - IDS/IPS: Suricata with ET rules
```

---

## 4. SOFTWARE STACK DETAILS

### 4.1 Core Services (Docker Compose)

```yaml
version: '3.8'

services:
  # Free Intelligence Core
  fi-core:
    image: aurity/fi-core:1.0
    environment:
      - DATABASE_URL=postgresql://fi:${DB_PASSWORD}@postgres:5432/fi_prod
      - MINIO_ENDPOINT=minio:9000
      - QDRANT_URL=http://qdrant:6333
      - REDIS_URL=redis://redis:6379
      - WHISPER_MODEL=large-v3
      - CLAUDE_API_KEY=${CLAUDE_KEY}
    volumes:
      - /volume1/aurity/audio:/data/audio:rw
      - /volume1/aurity/documents:/data/documents:rw
    devices:
      - /dev/dri:/dev/dri  # Intel Quick Sync
    deploy:
      resources:
        limits:
          memory: 8G
        reservations:
          memory: 4G
    restart: unless-stopped

  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=fi_prod
      - POSTGRES_USER=fi
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - /volume1/aurity/postgres:/var/lib/postgresql/data
    command: >
      postgres
      -c shared_buffers=2GB
      -c effective_cache_size=6GB
      -c maintenance_work_mem=512MB
      -c checkpoint_completion_target=0.9
      -c wal_buffers=16MB
      -c default_statistics_target=100
      -c random_page_cost=1.1
      -c effective_io_concurrency=200
    restart: unless-stopped

  # MinIO Object Storage
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      - MINIO_ROOT_USER=admin
      - MINIO_ROOT_PASSWORD=${MINIO_PASSWORD}
    volumes:
      - /volume1/aurity/minio:/data
    ports:
      - "9000:9000"
      - "9001:9001"
    restart: unless-stopped

  # Qdrant Vector DB
  qdrant:
    image: qdrant/qdrant:v1.7.0
    volumes:
      - /volume1/aurity/qdrant:/qdrant/storage
    restart: unless-stopped

  # Redis Cache
  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 2gb --maxmemory-policy allkeys-lru
    volumes:
      - /volume1/aurity/redis:/data
    restart: unless-stopped

  # TimescaleDB (IoT metrics)
  timescaledb:
    image: timescale/timescaledb:latest-pg15
    environment:
      - POSTGRES_DB=metrics
      - POSTGRES_USER=metrics
      - POSTGRES_PASSWORD=${METRICS_DB_PASSWORD}
    volumes:
      - /volume1/aurity/timescale:/var/lib/postgresql/data
    restart: unless-stopped

  # Grafana Dashboard
  grafana:
    image: grafana/grafana:latest
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
      - GF_INSTALL_PLUGINS=grafana-clock-panel
    volumes:
      - /volume1/aurity/grafana:/var/lib/grafana
    ports:
      - "3000:3000"
    restart: unless-stopped

  # Meilisearch Full-Text
  meilisearch:
    image: getmeili/meilisearch:v1.5
    environment:
      - MEILI_MASTER_KEY=${MEILI_KEY}
      - MEILI_NO_ANALYTICS=true
    volumes:
      - /volume1/aurity/meilisearch:/meili_data
    restart: unless-stopped

  # MQTT Broker (IoT)
  mosquitto:
    image: eclipse-mosquitto:2
    volumes:
      - /volume1/aurity/mosquitto/config:/mosquitto/config
      - /volume1/aurity/mosquitto/data:/mosquitto/data
    ports:
      - "1883:1883"
      - "8883:8883"  # TLS
    restart: unless-stopped

  # Nginx Reverse Proxy
  nginx:
    image: nginx:alpine
    volumes:
      - /volume1/aurity/nginx/conf.d:/etc/nginx/conf.d:ro
      - /volume1/aurity/nginx/ssl:/etc/nginx/ssl:ro
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - fi-core
      - grafana
      - minio
    restart: unless-stopped

volumes:
  postgres_data:
  minio_data:
  qdrant_data:
  redis_data:
```

### 4.2 Whisper Local Setup

```dockerfile
# Dockerfile para Whisper con GPU
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir \
    openai-whisper==20231117 \
    faster-whisper==0.10.0 \
    torch==2.1.0 \
    torchaudio==2.1.0

WORKDIR /app
COPY whisper_server.py .

CMD ["python3", "whisper_server.py"]
```

```python
# whisper_server.py
from faster_whisper import WhisperModel
from fastapi import FastAPI, UploadFile
import io

app = FastAPI()

# Load model once at startup
model = WhisperModel(
    "large-v3",
    device="cuda",
    compute_type="float16",
    cpu_threads=4,
    num_workers=2
)

@app.post("/transcribe")
async def transcribe(audio: UploadFile):
    """Transcribe audio file"""

    audio_bytes = await audio.read()
    audio_io = io.BytesIO(audio_bytes)

    segments, info = model.transcribe(
        audio_io,
        language="es",
        beam_size=5,
        best_of=5,
        temperature=0.0,
        vad_filter=True,  # Built-in VAD
        vad_parameters={
            "threshold": 0.5,
            "min_speech_duration_ms": 250
        }
    )

    transcript = []
    for segment in segments:
        transcript.append({
            "start": segment.start,
            "end": segment.end,
            "text": segment.text,
            "confidence": segment.avg_logprob
        })

    return {
        "language": info.language,
        "duration": info.duration,
        "segments": transcript
    }
```

---

## 5. SECURITY & COMPLIANCE

### 5.1 Data Protection

**Encryption:**
```yaml
At Rest:
  - NAS volumes: Btrfs encryption (AES-256-XTS)
  - Database: PostgreSQL pgcrypto extension
  - Objects: MinIO server-side encryption (SSE-C)
  - Backups: GPG encryption before offsite

In Transit:
  - TLS 1.3 for all HTTP traffic
  - WireGuard VPN for remote access
  - MQTT over TLS for IoT sensors
  - Bluetooth pairing with PIN

Keys Management:
  - Master key: Stored in HSM or Synology KMS
  - Per-clinic keys: Derived with HKDF
  - Rotation: Annual mandatory
  - Backup: Split-key escrow (3 of 5 recovery)
```

**Access Control:**
```yaml
Network:
  - Firewall: Default deny, explicit allow
  - Segmentation: VLANs por clinical/admin/IoT
  - IDS: Suricata with daily rule updates
  - Rate limiting: Fail2ban for SSH/HTTP

Application:
  - Authentication: JWT tokens, 15min expiry
  - MFA: TOTP (Google Authenticator)
  - Password: Argon2id, min 12 chars
  - Session: Timeout 30min inactivity

Database:
  - Row-level security: PostgreSQL RLS
  - Query logging: All SELECT/UPDATE/DELETE
  - Prepared statements: SQL injection prevention
  - Least privilege: Service accounts por role
```

### 5.2 Audit Trail

**Comprehensive Logging:**
```python
# Audit decorator
from functools import wraps
from flask import request, g
import logging

audit_logger = logging.getLogger('audit')

def audit_log(action: str, resource_type: str):
    """Decorator para auditar acciones"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            resource_id = kwargs.get('id') or request.view_args.get('id')

            try:
                result = f(*args, **kwargs)
                success = True
                error = None
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                audit_logger.info({
                    "user_id": g.user.id,
                    "action": action,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "ip": request.remote_addr,
                    "user_agent": request.user_agent.string,
                    "success": success,
                    "error": error
                })

            return result
        return wrapper
    return decorator

# Usage
@app.route('/api/records/<uuid:id>', methods=['GET'])
@audit_log('READ', 'clinical_record')
def get_record(id):
    record = Record.query.get_or_404(id)
    verify_access(g.user, record)
    return jsonify(record.to_dict())
```

### 5.3 Compliance Checklist

**HIPAA Equivalent (NOM-024-SSA3):**
```yaml
Administrative:
  - [x] Políticas seguridad escritas
  - [x] Oficial de privacidad designado
  - [x] Capacitación anual personal
  - [x] Acuerdos confidencialidad firmados
  - [x] Plan respuesta incidentes

Physical:
  - [x] NAS en cuarto con acceso restringido
  - [x] Cerraduras electrónicas con log
  - [x] CCTV 24/7 con retención 30 días
  - [x] Destrucción segura medios (shredding)

Technical:
  - [x] Cifrado AES-256 at rest/transit
  - [x] MFA obligatorio para acceso
  - [x] Audit log immutable (WORM)
  - [x] Backups cifrados offsite
  - [x] Pruebas penetración anuales

Documentation:
  - [x] Matriz de riesgos actualizada
  - [x] Procedimientos operativos estándar
  - [x] Registros de auditoría accesibles
  - [x] Evidencia de capacitaciones
```

---

## 6. OPERATIONS & MONITORING

### 6.1 SLO Definitions

```yaml
Availability:
  target: 99.5% monthly
  measurement: Uptime monitoring cada 1min
  budget: 3.6 horas downtime/mes
  escalation: >2 horas → management alert

Latency:
  ingestion_p95: <2s
  transcription_p95: <5s
  search_p99: <500ms
  api_response_p95: <200ms

Reliability:
  backup_success: 100% daily
  data_loss: 0 bytes tolerance
  integrity_errors: <0.01% verificaciones

Capacity:
  storage_warning: 70% used
  storage_critical: 85% used
  cpu_sustained: <60% average
  memory_sustained: <70% average
```

### 6.2 Monitoring Stack

```yaml
# Prometheus config
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'fi-core'
    static_configs:
      - targets: ['fi-core:8080']

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'nas'
    static_configs:
      - targets: ['synology-exporter:9001']

  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

rule_files:
  - /etc/prometheus/alerts/*.yml
```

**Critical Alerts:**
```yaml
# alerts/critical.yml
groups:
  - name: critical
    interval: 1m
    rules:
      - alert: ServiceDown
        expr: up == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.job }} down"

      - alert: DiskSpaceCritical
        expr: node_filesystem_avail_bytes / node_filesystem_size_bytes < 0.15
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Disk space critical on {{ $labels.instance }}"

      - alert: BackupFailed
        expr: backup_last_success > 86400
        labels:
          severity: critical
        annotations:
          summary: "Backup has not succeeded in 24h"

      - alert: IntegrityCheckFailed
        expr: integrity_check_errors > 0
        labels:
          severity: critical
        annotations:
          summary: "{{ $value }} integrity check failures detected"
```

### 6.3 Incident Response

**Runbooks:**

```markdown
# RUNBOOK: Service Down

## Detection
- Alert: ServiceDown fires
- Dashboard: Grafana shows service red

## Triage
1. Check container status: `docker ps -a | grep fi-core`
2. View logs: `docker logs --tail=100 fi-core`
3. Check resource usage: `htop`, `df -h`

## Common Issues

### Out of Memory
- Symptoms: Container killed, logs show OOM
- Fix:
  ```bash
  docker-compose restart fi-core
  # Increase memory limit in compose if recurring
  ```

### Database Connection Lost
- Symptoms: "connection refused" in logs
- Fix:
  ```bash
  docker-compose restart postgres
  # Wait 30s for recovery
  docker-compose restart fi-core
  ```

### Disk Full
- Symptoms: "no space left" errors
- Fix:
  ```bash
  # Emergency: Delete old logs
  find /var/log -name "*.log" -mtime +7 -delete

  # Long-term: Trigger archival
  docker-compose exec fi-core /scripts/archive_old_data.sh
  ```

## Escalation
- If not resolved in 15min → Call on-call engineer
- If downtime >1h → Notify clinic admin
- If data loss suspected → STOP, call security team
```

---

## 7. COST ANALYSIS

### 7.1 Startup Costs (Single Clinic)

```yaml
Hardware:
  NAS DS923+ setup: $2,500
  Network upgrade: $800
  UPS + surge protection: $400
  ESP32 wearables (5 units): $100
  Subtotal: $3,800

Software:
  Initial development: $0 (internal)
  SSL certificates: $50/year
  Domain registration: $15/year
  Subtotal: $65/year

Professional Services:
  Installation & training: $1,200
  Network configuration: $500
  Subtotal: $1,700

TOTAL INITIAL: $5,565
```

### 7.2 Monthly Operating Costs

```yaml
Infrastructure:
  Internet business (100/20 Mbps): $80
  Electricity NAS (est.): $15
  Cloud backup (Backblaze 500GB): $5
  SSL renewal (monthly): $5
  Subtotal: $105

Software Licenses:
  FI-Core (Fase 3): $200
  Claude API (est. 100k tokens/día): $30
  Monitoring tools: $0 (open source)
  Subtotal: $230

Support & Maintenance:
  Monthly check-in call: $100
  Software updates: included
  Hardware warranty: included
  Subtotal: $100

TOTAL MONTHLY: $435/mes
```

### 7.3 Revenue Projections (Per Clinic)

```yaml
Fase 1-2 (Meses 1-8):
  FI-Cold: $60/mes
  FI-Entry: $40/mes
  FI-Assets: $40/mes
  FI-Calibration: $35/mes
  FI-Logistics: $25/mes
  Monthly subtotal: $200/mes

  Margin: $200 - $105 infra = $95/mes
  8 meses: $760 profit

Fase 3 (Meses 9-14):
  Fase 1-2 modules: $200/mes
  FI-Core license: $200/mes
  Setup fee (one-time): $500
  Monthly subtotal: $400/mes + $500

  Margin: $400 - $335 costs = $65/mes
  6 meses: $390 + $500 = $890 profit

Fase 4 (Meses 15+):
  All previous: $400/mes
  FI-Tele Pro base: $150/mes
  FI-Tele per-consult: $2 x 200 = $400/mes
  FI-Lab Connect: $100/mes
  Monthly subtotal: $1,050/mes

  Margin: $1,050 - $335 = $715/mes
  Annual: $8,580 profit/clinic

Break-even: Mes 13 (con 10 clínicas piloto)
```

---

## 8. DEPLOYMENT GUIDE

### 8.1 Pre-Installation Checklist

```markdown
- [ ] Network assessment completed
  - [ ] Fiber optic connection confirmed
  - [ ] Static IP assigned
  - [ ] VLANs configured
  - [ ] WiFi coverage tested

- [ ] NAS hardware received
  - [ ] Drives installed (RAID6)
  - [ ] RAM upgraded to 32GB
  - [ ] UPS connected and tested
  - [ ] Physical security verified

- [ ] Software prepared
  - [ ] Docker images pulled
  - [ ] Configuration files reviewed
  - [ ] SSL certificates obtained
  - [ ] Backup targets configured

- [ ] Personnel trained
  - [ ] Admin user created
  - [ ] Roles assigned
  - [ ] Passwords documented (vault)
  - [ ] Emergency contacts listed
```

### 8.2 Installation Steps

```bash
#!/bin/bash
# install_aurity.sh - Automated deployment

set -e

echo "=== Aurity Installation Script ==="

# 1. System updates
echo "[1/10] Updating system..."
sudo apt update && sudo apt upgrade -y

# 2. Install Docker
echo "[2/10] Installing Docker..."
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
sudo systemctl enable docker

# 3. Install Docker Compose
echo "[3/10] Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 4. Create directory structure
echo "[4/10] Creating directories..."
sudo mkdir -p /volume1/aurity/{audio,documents,postgres,minio,qdrant,redis,grafana}
sudo chown -R 1024:100 /volume1/aurity  # Synology UID/GID

# 5. Generate secrets
echo "[5/10] Generating secrets..."
cat > .env <<EOF
DB_PASSWORD=$(openssl rand -base64 32)
MINIO_PASSWORD=$(openssl rand -base64 32)
METRICS_DB_PASSWORD=$(openssl rand -base64 32)
GRAFANA_PASSWORD=$(openssl rand -base64 32)
MEILI_KEY=$(openssl rand -base64 32)
CLAUDE_API_KEY=<YOUR_KEY_HERE>
EOF

# 6. Deploy containers
echo "[6/10] Starting services..."
docker-compose up -d

# 7. Wait for services
echo "[7/10] Waiting for services to be healthy..."
sleep 30

# 8. Initialize database
echo "[8/10] Initializing database..."
docker-compose exec -T postgres psql -U fi fi_prod < schema.sql

# 9. Load initial data
echo "[9/10] Loading reference data..."
docker-compose exec -T fi-core python /app/scripts/load_fixtures.py

# 10. Verify installation
echo "[10/10] Verifying installation..."
docker-compose ps
curl -f http://localhost:8080/health || echo "Warning: API not responding"

echo ""
echo "=== Installation Complete ==="
echo "Access Grafana: http://$(hostname -I | awk '{print $1}'):3000"
echo "Default credentials in .env file"
echo ""
echo "Next steps:"
echo "1. Change all default passwords"
echo "2. Configure SSL certificates"
echo "3. Set up backups"
echo "4. Train staff"
```

### 8.3 Post-Installation Tasks

```yaml
Week 1:
  - [ ] SSL certificates installed
  - [ ] External access configured (VPN)
  - [ ] First backup verified
  - [ ] Monitoring alerts tested
  - [ ] Admin trained on interface

Week 2:
  - [ ] 5 ESP32 wearables configured
  - [ ] Mobile apps installed on physician phones
  - [ ] Test consultation recorded & transcribed
  - [ ] Search functionality validated
  - [ ] Audit log review completed

Week 3:
  - [ ] Physician training (2 hours)
  - [ ] Practice consultations (non-patient)
  - [ ] Workflow adjustments
  - [ ] Performance tuning
  - [ ] Go-live planning

Week 4:
  - [ ] Soft launch with 2 physicians
  - [ ] Daily check-ins
  - [ ] Issue tracking
  - [ ] Feedback collection
  - [ ] Full launch approval
```

---

## 9. QUALITY ASSURANCE

### 9.1 Testing Strategy

```yaml
Unit Tests:
  coverage: >80%
  framework: pytest
  mocks: Yes (external APIs)
  run: On every commit

Integration Tests:
  scope: Service-to-service
  database: Test instance
  duration: ~15min
  run: On PR merge

End-to-End Tests:
  scenarios:
    - Complete consultation flow
    - Document upload & search
    - User permission enforcement
    - Backup & restore
  frequency: Nightly
  environment: Staging NAS

Performance Tests:
  tool: Locust
  scenarios:
    - 10 concurrent consultations
    - 100 searches/second
    - 1000 document ingestions/hour
  baseline: Established in beta
  regression: ±10% tolerance

Security Tests:
  SAST: SonarQube on every build
  DAST: OWASP ZAP weekly
  Dependency: Snyk daily scans
  Penetration: Annual external audit
```

### 9.2 Acceptance Criteria

**For Production Release:**

```yaml
Functional:
  - [ ] All core user stories completed
  - [ ] Zero P0/P1 bugs open
  - [ ] Regulatory requirements met
  - [ ] User documentation complete
  - [ ] Training materials ready

Performance:
  - [ ] SLO targets met in load tests
  - [ ] Database queries <100ms p95
  - [ ] Transcription <5s latency
  - [ ] Search results <500ms

Security:
  - [ ] Penetration test passed
  - [ ] Encryption verified everywhere
  - [ ] Audit logging functional
  - [ ] Backup/restore validated
  - [ ] Incident response tested

Operational:
  - [ ] Monitoring dashboards live
  - [ ] Alerting rules configured
  - [ ] Runbooks documented
  - [ ] On-call rotation established
  - [ ] Rollback procedure tested
```

---

## 10. ROADMAP MILESTONES

```yaml
Q1 2025: Foundation
  - [x] Architecture design
  - [x] Free Intelligence integration
  - [ ] Fase 1 modules (FI-Cold, FI-Entry)
  - [ ] 3 pilot clinics onboarded
  - [ ] Revenue: $600/mes ($200 x 3)

Q2 2025: Expansion
  - [ ] Fase 2 modules (Assets, Calibration, Logistics)
  - [ ] 10 total clinics
  - [ ] ESP32 wearable production (100 units)
  - [ ] Revenue: $2,000/mes

Q3 2025: Clinical Core
  - [ ] Fase 3 FI-Core deployment
  - [ ] Whisper local optimized
  - [ ] 25 total clinics
  - [ ] Revenue: $10,000/mes

Q4 2025: Compliance Sprint
  - [ ] ISO 27001 audit initiated
  - [ ] NOM-024-SSA3 application
  - [ ] COFEPRIS registration
  - [ ] 50 total clinics
  - [ ] Revenue: $20,000/mes

Q1-Q2 2026: Regulated Services
  - [ ] Certifications obtained
  - [ ] Fase 4 modules launch
  - [ ] HL7/FHIR connectors
  - [ ] 100 total clinics
  - [ ] Revenue: $100,000/mes

Q3+ 2026: Scale
  - [ ] Multi-country expansion
  - [ ] White-label partnerships
  - [ ] Federation between networks
  - [ ] 500+ clinics
  - [ ] Revenue: $500,000+/mes
```

---

## 11. RISK MANAGEMENT

### 11.1 Technical Risks

```yaml
Risk: NAS hardware failure
  Probability: Medium
  Impact: High
  Mitigation:
    - RAID6 protects against 2 disk failures
    - Hot spare disk configured
    - 4-hour RTO with vendor support
    - Offsite backups for DR

Risk: Network connectivity loss
  Probability: Low (business fiber)
  Impact: High
  Mitigation:
    - 4G LTE backup connection
    - Local queuing during outage
    - Offline mode for critical operations
    - SLA with ISP (<4h repair)

Risk: Whisper transcription errors
  Probability: Medium
  Impact: Medium
  Mitigation:
    - Physician review before finalization
    - Confidence scores displayed
    - Manual correction interface
    - Continuous model fine-tuning

Risk: Data breach
  Probability: Low
  Impact: Critical
  Mitigation:
    - Multi-layer encryption
    - MFA enforced
    - Annual penetration tests
    - Cyber insurance coverage
    - Incident response plan tested
```

### 11.2 Business Risks

```yaml
Risk: Slow adoption by physicians
  Probability: Medium
  Impact: High
  Mitigation:
    - Hands-on training included
    - Demonstrable time savings
    - Gradual rollout (1-2 doctors first)
    - Incentive structure for early adopters

Risk: Regulatory changes
  Probability: Low
  Impact: High
  Mitigation:
    - Legal counsel on retainer
    - Architecture flexible for changes
    - Compliance buffer in roadmap
    - Industry association membership

Risk: Competitor with cloud solution
  Probability: High
  Impact: Medium
  Mitigation:
    - Emphasize data sovereignty
    - Lower long-term TCO
    - No vendor lock-in
    - Superior latency/privacy

Risk: Economic downturn affecting clinics
  Probability: Medium
  Impact: High
  Mitigation:
    - Phase 1-2 ROI immediate
    - Flexible payment terms
    - Focus on cost reduction, not luxury
    - Essential service positioning
```

---

## 12. SUCCESS METRICS

### 12.1 Product KPIs

```yaml
Adoption:
  - Daily Active Physicians: Target 80%
  - Consultations per physician/day: Target 8+
  - Wearable usage rate: Target 90%
  - Feature utilization: >60% use search weekly

Quality:
  - Transcription accuracy: >92% WER
  - Search relevance: >85% in top-3 results
  - Uptime: >99.5% monthly
  - Bug escape rate: <2% to production

Efficiency:
  - Time to finalize note: <5 min (vs 20 min manual)
  - Document retrieval time: <30s (vs 5 min manual)
  - Audit preparation time: -80% vs paper

Financial:
  - Customer Acquisition Cost: <$500
  - Lifetime Value: >$50,000 (5 years)
  - Churn rate: <10% annual
  - Gross margin: >65%
```

### 12.2 Clinical Outcomes

```yaml
Patient Safety:
  - Medication errors detected: Track incidents prevented
  - Critical result alerts: Response time <15 min
  - Documentation completeness: >95% required fields

Physician Satisfaction:
  - NPS (Net Promoter Score): Target >50
  - Time saved per day: Target 2+ hours
  - Willingness to recommend: Target >80%
  - Renewal rate: Target >90%

Operational:
  - Chart completion rate: >95% within 24h
  - Audit findings: -50% vs baseline
  - Insurance claim denials: -30% due to documentation
```

---

## 13. GLOSSARY

```yaml
Aurity: Artificial United Robust Intelligence for Telemedicine Yield
FI: Free Intelligence - Sistema nervioso técnico local
PHI: Protected Health Information
NAS: Network Attached Storage
VAD: Voice Activity Detection
WORM: Write Once Read Many
SLO: Service Level Objective
SLI: Service Level Indicator
RTO: Recovery Time Objective
RPO: Recovery Point Objective
HL7: Health Level 7 (messaging standard)
FHIR: Fast Healthcare Interoperability Resources
DICOM: Digital Imaging and Communications in Medicine
NOM: Norma Oficial Mexicana
COFEPRIS: Comisión Federal para la Protección contra Riesgos Sanitarios
```

---

## 14. APPENDICES

### 14.1 Sample Data Structures

```json
// Consultation Manifest
{
  "manifest_version": "1.0",
  "consultation_id": "550e8400-e29b-41d4-a716-446655440000",
  "clinic_id": "clinic-mx-001",
  "timestamp_start": "2025-10-25T09:00:00Z",
  "timestamp_end": "2025-10-25T09:27:34Z",
  "participants": [
    {
      "role": "physician",
      "id": "MD-001",
      "name_encrypted": "U2FsdGVkX1...",
      "consent_obtained": true,
      "consent_timestamp": "2025-10-25T08:55:00Z"
    },
    {
      "role": "patient",
      "pseudonym": "PAT-xK4j9",
      "consent_obtained": true,
      "consent_timestamp": "2025-10-25T08:56:00Z"
    }
  ],
  "segments": [
    {
      "segment_id": 1,
      "start_time": "2025-10-25T09:00:00Z",
      "duration_seconds": 90,
      "speaker": "physician",
      "has_audio": true,
      "has_video": false,
      "sha256_audio": "7a3c4e2f9b1d8a5e...",
      "storage_path": "minio://consultations/2025/10/25/550e8400.../seg001.opus"
    }
  ],
  "transcripts": {
    "enabled": true,
    "model": "whisper-large-v3",
    "language": "es-MX",
    "segments_transcribed": 12,
    "total_words": 1847,
    "avg_confidence": 0.94
  },
  "clinical_markers": [
    {
      "timestamp": "2025-10-25T09:03:12Z",
      "type": "chief_complaint",
      "text": "Dolor abdominal 3 días evolución"
    },
    {
      "timestamp": "2025-10-25T09:08:45Z",
      "type": "physical_exam",
      "text": "Abdomen: blando, depresible, dolor a palpación en FID"
    },
    {
      "timestamp": "2025-10-25T09:15:30Z",
      "type": "diagnosis",
      "text": "Probable apendicitis aguda"
    },
    {
      "timestamp": "2025-10-25T09:20:00Z",
      "type": "plan",
      "text": "Referencia a cirugía, laboratorios urgentes, USG abdominal"
    }
  ],
  "manifest_signature": {
    "algorithm": "RSA-SHA256",
    "public_key_fingerprint": "clinic-mx-001:2025",
    "signature": "MIIBIjANBgkqhki...",
    "signed_at": "2025-10-25T09:27:35Z"
  },
  "verification_url": "https://aurity.clinic/verify/550e8400"
}
```

```json
// Laboratory Result Structure
{
  "lab_result_id": "LAB-2025-10-25-003",
  "order_id": "ORD-2025-10-24-089",
  "patient_pseudonym": "PAT-xK4j9",
  "clinic_id": "clinic-mx-001",
  "external_lab": {
    "name": "Laboratorio Clínico del Chopo",
    "nuc": "123456789",
    "address": "Av. Revolución 1234, CDMX"
  },
  "collection_datetime": "2025-10-24T08:30:00Z",
  "result_datetime": "2025-10-25T14:20:00Z",
  "test_panels": [
    {
      "panel_name": "Química Sanguínea 6 elementos",
      "loinc_code": "24323-8",
      "tests": [
        {
          "name": "Glucosa",
          "loinc_code": "2345-7",
          "value": 126,
          "unit": "mg/dL",
          "reference_range": {
            "low": 70,
            "high": 100
          },
          "interpretation": "HIGH",
          "critical": false,
          "flags": ["H"]
        },
        {
          "name": "Creatinina",
          "loinc_code": "2160-0",
          "value": 1.2,
          "unit": "mg/dL",
          "reference_range": {
            "low": 0.7,
            "high": 1.3
          },
          "interpretation": "NORMAL",
          "critical": false,
          "flags": []
        },
        {
          "name": "Potasio",
          "loinc_code": "2823-3",
          "value": 6.2,
          "unit": "mEq/L",
          "reference_range": {
            "low": 3.5,
            "high": 5.0
          },
          "interpretation": "CRITICAL",
          "critical": true,
          "flags": ["HH", "CRIT"],
          "alert_generated": true,
          "alert_timestamp": "2025-10-25T14:21:00Z",
          "alert_acknowledged_by": "MD-001",
          "alert_acknowledged_at": "2025-10-25T14:23:00Z"
        }
      ]
    }
  ],
  "pdf_original": {
    "filename": "LAB-2025-10-25-003.pdf",
    "sha256": "9f3e7a1c4d8b2e5a...",
    "size_bytes": 245678,
    "storage_path": "minio://labs/2025/10/25/LAB-003.pdf"
  },
  "hl7_message": {
    "version": "2.5",
    "sha256": "1a2b3c4d5e6f7a8b...",
    "storage_path": "minio://hl7/2025/10/25/LAB-003.hl7"
  },
  "embedding_indexed": true,
  "searchable_text": "Química sanguínea glucosa 126 elevada creatinina 1.2 normal potasio 6.2 crítico hiperkalemia...",
  "indexed_at": "2025-10-25T14:22:00Z"
}
```

```json
// Prescription Structure
{
  "prescription_id": "RX-2025-10-25-012",
  "version": 1,
  "previous_version": null,
  "consultation_id": "550e8400-e29b-41d4-a716-446655440000",
  "physician": {
    "id": "MD-001",
    "name": "Dr. Juan Pérez González",
    "cedula_profesional": "1234567",
    "especialidad": "Medicina Interna",
    "firma_digital": {
      "certificate_fingerprint": "A1:B2:C3:D4...",
      "issuer": "SAT e.firma",
      "valid_until": "2027-10-20T00:00:00Z"
    }
  },
  "patient": {
    "pseudonym": "PAT-xK4j9",
    "age": 45,
    "sex": "M",
    "allergies": ["Penicilina"]
  },
  "issued_datetime": "2025-10-25T09:25:00Z",
  "valid_until": "2025-11-25T23:59:59Z",
  "medications": [
    {
      "item_number": 1,
      "medication_name": "Metformina",
      "active_ingredient": "Metformina Clorhidrato",
      "presentation": "Tabletas",
      "strength": "850 mg",
      "quantity": 60,
      "unit": "tabletas",
      "directions": {
        "dose": "1 tableta",
        "frequency": "cada 12 horas",
        "route": "vía oral",
        "duration": "30 días",
        "instructions": "Tomar con alimentos. No suspender sin indicación médica."
      },
      "substitution_allowed": true,
      "controlled_substance": false
    },
    {
      "item_number": 2,
      "medication_name": "Losartán",
      "active_ingredient": "Losartán Potásico",
      "presentation": "Tabletas",
      "strength": "50 mg",
      "quantity": 30,
      "unit": "tabletas",
      "directions": {
        "dose": "1 tableta",
        "frequency": "cada 24 horas",
        "route": "vía oral",
        "timing": "en ayunas",
        "duration": "30 días",
        "instructions": "Control de presión arterial semanal."
      },
      "substitution_allowed": true,
      "controlled_substance": false
    }
  ],
  "diagnosis_codes": [
    {
      "code": "E11.9",
      "system": "ICD-10",
      "description": "Diabetes mellitus tipo 2 sin complicaciones"
    },
    {
      "code": "I10",
      "system": "ICD-10",
      "description": "Hipertensión arterial esencial"
    }
  ],
  "notes": "Control en 1 mes con resultados de laboratorio. Dieta y ejercicio recomendados.",
  "qr_code": {
    "data": "https://aurity.clinic/rx/RX-2025-10-25-012/verify",
    "image_base64": "iVBORw0KGgoAAAANSUhEUgAA..."
  },
  "hashes": {
    "content_sha256": "b8e4f2a9c1d7e3f5...",
    "signed_sha256": "c9f5a3b2e8d1f4a6..."
  },
  "immutable": true,
  "legal_hold": false,
  "blockchain_entry": {
    "block_number": 12847,
    "previous_block_hash": "8a7c4f2e9d1b5a3e...",
    "merkle_root": "7f3e2a9c8d1b4f5a..."
  }
}
```

### 14.2 API Endpoints Reference

```yaml
Authentication:
  POST /api/v1/auth/login
    Request: { "email": "...", "password": "...", "mfa_code": "..." }
    Response: { "access_token": "...", "refresh_token": "...", "expires_in": 900 }

  POST /api/v1/auth/refresh
    Request: { "refresh_token": "..." }
    Response: { "access_token": "...", "expires_in": 900 }

Consultations:
  POST /api/v1/consultations/start
    Request: { "patient_id": "...", "consultation_type": "..." }
    Response: { "consultation_id": "...", "session_token": "..." }

  POST /api/v1/consultations/{id}/segments
    Request: multipart/form-data (audio/video chunk)
    Response: { "segment_id": "...", "hash": "...", "stored": true }

  GET /api/v1/consultations/{id}/transcript
    Response: { "segments": [...], "markers": [...], "manifest": {...} }

  POST /api/v1/consultations/{id}/finalize
    Response: { "manifest": {...}, "signature": "...", "verification_url": "..." }

Documents:
  POST /api/v1/documents/upload
    Request: multipart/form-data (PDF/DICOM/HL7)
    Response: { "document_id": "...", "hash": "...", "indexed": true }

  GET /api/v1/documents/{id}
    Response: Binary (PDF/DICOM) or JSON (structured)

  GET /api/v1/documents/{id}/verify
    Response: { "valid": true, "hash_matches": true, "signature_valid": true }

Search:
  GET /api/v1/search?q={query}&mode={structured|fulltext|semantic}
    Response: { "results": [...], "total": 123, "took_ms": 45 }

  GET /api/v1/search/patients/{id}?q={query}
    Response: { "results": [...], "timeline": [...] }

Prescriptions:
  POST /api/v1/prescriptions/create
    Request: { "consultation_id": "...", "medications": [...], ... }
    Response: { "prescription_id": "...", "qr_code": "...", "pdf_url": "..." }

  GET /api/v1/prescriptions/{id}/verify
    Response: { "valid": true, "revoked": false, "physician": {...} }

Labs:
  POST /api/v1/labs/ingest
    Request: { "hl7_message": "..." } or multipart PDF
    Response: { "lab_id": "...", "critical_alerts": [...] }

  GET /api/v1/labs/{id}
    Response: { "structured": {...}, "pdf_url": "...", "critical": [...] }

Audit:
  GET /api/v1/audit/logs?from={date}&to={date}&user_id={id}
    Response: { "logs": [...], "total": 456 }

  GET /api/v1/audit/access/{resource_id}
    Response: { "accesses": [...], "exports": [...] }

Governance:
  POST /api/v1/governance/legal-hold
    Request: { "resource_id": "...", "reason": "..." }
    Response: { "hold_id": "...", "applied_at": "..." }

  DELETE /api/v1/governance/legal-hold/{id}
    Response: { "released_at": "...", "released_by": "..." }

Metrics:
  GET /api/v1/metrics/slo
    Response: { "availability": 99.7, "latency_p95": 1.8, ... }

  GET /api/v1/metrics/usage
    Response: { "storage_used_gb": 234, "consultations_today": 45, ... }
```

### 14.3 Database Schema Diagrams

```sql
-- Core Clinical Tables
CREATE TABLE clinics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    nuc VARCHAR(20) UNIQUE,
    address TEXT,
    phone VARCHAR(20),
    email VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID REFERENCES clinics(id),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('owner', 'compliance', 'medico', 'auditor')),
    mfa_secret VARCHAR(32),
    mfa_enabled BOOLEAN DEFAULT false,
    cedula_profesional VARCHAR(20),
    especialidad VARCHAR(100),
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ
);

CREATE TABLE patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID REFERENCES clinics(id),
    pseudonym VARCHAR(20) UNIQUE NOT NULL,
    encrypted_name BYTEA NOT NULL,
    encrypted_curp BYTEA,
    date_of_birth_encrypted BYTEA,
    sex CHAR(1) CHECK (sex IN ('M', 'F', 'O')),
    allergies TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE consultations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID REFERENCES clinics(id),
    patient_id UUID REFERENCES patients(id),
    physician_id UUID REFERENCES users(id),
    consultation_type VARCHAR(50) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    status VARCHAR(20) CHECK (status IN ('active', 'completed', 'cancelled')),
    chief_complaint TEXT,
    manifest JSONB,
    manifest_signature TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE consultation_segments (
    id BIGSERIAL PRIMARY KEY,
    consultation_id UUID REFERENCES consultations(id),
    segment_number INT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    duration_seconds INT NOT NULL,
    speaker VARCHAR(20),
    audio_path TEXT,
    video_path TEXT,
    sha256_audio CHAR(64),
    sha256_video CHAR(64),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (consultation_id, segment_number)
);

CREATE TABLE transcripts (
    id BIGSERIAL PRIMARY KEY,
    segment_id BIGINT REFERENCES consultation_segments(id),
    text TEXT NOT NULL,
    language VARCHAR(10) DEFAULT 'es-MX',
    confidence DECIMAL(4,3),
    model_version VARCHAR(50),
    start_time DECIMAL(10,3),
    end_time DECIMAL(10,3),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE clinical_markers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    consultation_id UUID REFERENCES consultations(id),
    marker_type VARCHAR(50) NOT NULL CHECK (marker_type IN ('chief_complaint', 'symptom', 'physical_exam', 'diagnosis', 'plan')),
    timestamp TIMESTAMPTZ NOT NULL,
    text TEXT NOT NULL,
    confidence DECIMAL(4,3),
    created_by VARCHAR(20) DEFAULT 'ai',
    verified_by UUID REFERENCES users(id),
    verified_at TIMESTAMPTZ
);

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID REFERENCES clinics(id),
    patient_id UUID REFERENCES patients(id),
    consultation_id UUID REFERENCES consultations(id),
    document_type VARCHAR(50) NOT NULL CHECK (document_type IN ('prescription', 'lab', 'imaging', 'note', 'consent', 'other')),
    filename VARCHAR(255),
    mime_type VARCHAR(100),
    size_bytes BIGINT,
    storage_path TEXT NOT NULL,
    sha256 CHAR(64) NOT NULL,
    metadata JSONB,
    indexed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE prescriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id),
    consultation_id UUID REFERENCES consultations(id),
    physician_id UUID REFERENCES users(id),
    patient_id UUID REFERENCES patients(id),
    version INT NOT NULL DEFAULT 1,
    previous_version_id UUID REFERENCES prescriptions(id),
    issued_datetime TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ NOT NULL,
    medications JSONB NOT NULL,
    diagnosis_codes JSONB,
    notes TEXT,
    qr_code_data TEXT,
    signature TEXT,
    revoked BOOLEAN DEFAULT false,
    revoked_at TIMESTAMPTZ,
    revoked_by UUID REFERENCES users(id),
    revoke_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE lab_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id),
    patient_id UUID REFERENCES patients(id),
    order_id VARCHAR(50),
    external_lab_name VARCHAR(255),
    collection_datetime TIMESTAMPTZ,
    result_datetime TIMESTAMPTZ NOT NULL,
    test_panels JSONB NOT NULL,
    critical_results JSONB,
    hl7_message_path TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE critical_alerts (
    id BIGSERIAL PRIMARY KEY,
    lab_result_id UUID REFERENCES lab_results(id),
    test_name VARCHAR(100),
    test_value DECIMAL(10,3),
    unit VARCHAR(20),
    reference_range JSONB,
    severity VARCHAR(20) CHECK (severity IN ('critical', 'panic')),
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    acknowledged_by UUID REFERENCES users(id),
    acknowledged_at TIMESTAMPTZ,
    action_taken TEXT
);

CREATE TABLE embeddings (
    id BIGSERIAL PRIMARY KEY,
    document_id UUID REFERENCES documents(id),
    consultation_id UUID REFERENCES consultations(id),
    chunk_number INT,
    text TEXT NOT NULL,
    embedding_vector VECTOR(768),
    qdrant_point_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID NOT NULL,
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    success BOOLEAN NOT NULL,
    error_message TEXT
);

CREATE TABLE retention_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID REFERENCES clinics(id),
    resource_type VARCHAR(50) NOT NULL,
    category VARCHAR(50) NOT NULL CHECK (category IN ('operational', 'evidence', 'legal_hold')),
    retention_days INT NOT NULL,
    auto_delete BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE legal_holds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID NOT NULL,
    reason TEXT NOT NULL,
    applied_by UUID REFERENCES users(id),
    applied_at TIMESTAMPTZ DEFAULT NOW(),
    released_at TIMESTAMPTZ,
    released_by UUID REFERENCES users(id),
    release_notes TEXT
);

-- Indexes for performance
CREATE INDEX idx_consultations_patient ON consultations(patient_id);
CREATE INDEX idx_consultations_physician ON consultations(physician_id);
CREATE INDEX idx_consultations_started ON consultations(started_at DESC);
CREATE INDEX idx_segments_consultation ON consultation_segments(consultation_id);
CREATE INDEX idx_transcripts_segment ON transcripts(segment_id);
CREATE INDEX idx_documents_patient ON documents(patient_id);
CREATE INDEX idx_documents_consultation ON documents(consultation_id);
CREATE INDEX idx_documents_type ON documents(document_type);
CREATE INDEX idx_prescriptions_patient ON prescriptions(patient_id);
CREATE INDEX idx_lab_results_patient ON lab_results(patient_id);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_embeddings_document ON embeddings(document_id);

-- Full-text search
CREATE INDEX idx_transcripts_text ON transcripts USING gin(to_tsvector('spanish', text));
CREATE INDEX idx_clinical_markers_text ON clinical_markers USING gin(to_tsvector('spanish', text));
CREATE INDEX idx_documents_metadata ON documents USING gin(metadata);

-- Immutability rules for audit
CREATE RULE no_delete_audit_logs AS ON DELETE TO audit_logs DO INSTEAD NOTHING;
CREATE RULE no_update_audit_logs AS ON UPDATE TO audit_logs DO INSTEAD NOTHING;

-- Automatic timestamps
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$ LANGUAGE plpgsql;

CREATE TRIGGER set_updated_at BEFORE UPDATE ON clinics
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON patients
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```

---

## 15. CONCLUSION & NEXT STEPS

### 15.1 Executive Summary

Aurity representa una solución pragmática y escalable para telemedicina en LATAM que:

**Prioriza soberanía de datos** mediante arquitectura on-premise con NAS como núcleo
**Genera revenue inmediato** con módulos no-PHI (Fases 1-2) mientras construye capacidad regulatoria
**Integra Free Intelligence** como sistema nervioso técnico que convierte archivos en memoria clínica verificable
**Escala progresivamente** desde IoT simple hasta servicios clínicos completamente regulados
**Mantiene control total** del médico sobre información sensible, sin vendor lock-in

### 15.2 Diferenciadores Competitivos

```yaml
vs Soluciones Cloud (Docplanner, etc):
  ✓ Datos nunca salen de la clínica
  ✓ Sin costos recurrentes de storage
  ✓ Latencia <50ms vs segundos
  ✓ Funciona offline
  ✓ TCO 70% menor a 5 años

vs HIS/EHR tradicional:
  ✓ No reemplaza, complementa
  ✓ Capa de verdad técnica
  ✓ Integridad criptográfica
  ✓ Búsqueda semántica
  ✓ Timeline navegable

vs Transcripción manual:
  ✓ -75% tiempo documentación
  ✓ >92% accuracy vs ~80% humano
  ✓ Disponible 24/7
  ✓ Costo $0.02/min vs $2/min
  ✓ Trazabilidad completa
```

### 15.3 Immediate Action Items

**Semana 1: Preparación**
```bash
- [ ] Confirmar partnership Free Intelligence team
- [ ] Reservar dominios (aurity.ai, aurity.mx)
- [ ] Setup repositorio GitHub privado
- [ ] Contratar diseñador para branding
- [ ] Definir pricing final con CFO
```

**Semana 2-4: MVP Fase 1**
```bash
- [ ] Desarrollar FI-Cold (cadena frío)
- [ ] Desarrollar FI-Entry (accesos)
- [ ] Testing con 1 clínica piloto interna
- [ ] Documentación técnica completa
- [ ] Landing page marketing
```

**Mes 2: Primeros Clientes**
```bash
- [ ] Onboarding 3 clínicas piloto
- [ ] Setup NAS para cada una
- [ ] Capacitación médicos/admin
- [ ] Monitoreo 24/7 activo
- [ ] Recolección feedback semanal
```

**Mes 3: Iteración**
```bash
- [ ] Incorporar learnings pilotos
- [ ] Refinar UI/UX based on uso real
- [ ] Optimizar performance NAS
- [ ] Preparar Fase 2 módulos
- [ ] Proyecciones financieras actualizar
```

### 15.4 Open Questions for FI Team

```yaml
Integration:
  - ¿Free Intelligence soporta ARM64 (Synology NAS)?
  - ¿Cómo manejar state persistence en PostgreSQL vs Redis?
  - ¿Recomendaciones para action pipeline médico específico?

Performance:
  - ¿Benchmarks de FI con 10 consultas simultáneas?
  - ¿Límites de throughput para ingestion de audio?
  - ¿Estrategia de scaling horizontal en NAS?

Compliance:
  - ¿FI tiene consideraciones específicas HIPAA/NOM?
  - ¿Auditabilidad de actions Redux para evidencia legal?
  - ¿Recomendaciones para time-travel debugging en prod?

Roadmap:
  - ¿Planes de FI para HL7/FHIR integration?
  - ¿Soporte futuro para federated learning?
  - ¿Interoperabilidad entre instancias FI?
```

### 15.5 Success Criteria (6 Months)

```yaml
Technical:
  - [Target] 25 clínicas deployed
  - [Target] 99.5%+ uptime
  - [Target] 0 data loss incidents
  - [Target] <3s transcription latency
  - [Target] >92% Whisper accuracy

Business:
  - [Target] $20,000/mes recurring revenue
  - [Target] <10% churn rate
  - [Target] >4.5/5 physician satisfaction
  - [Target] 50+ physician active users
  - [Target] Break-even operacional

Regulatory:
  - [Target] ISO 27001 audit initiated
  - [Target] NOM-024-SSA3 application submitted
  - [Target] 0 compliance violations
  - [Target] Legal framework validated
  - [Target] Privacy impact assessment complete
```

---

## DOCUMENT METADATA

```yaml
Document: Aurity Low-Level Design (LLD)
Version: 1.0
Date: October 25, 2025
Authors: Aurity Technical Team + Free Intelligence Collaboration
Status: Draft for Review
Classification: Internal - Technical Specification
Pages: 15
Word Count: ~8,500 words

Revision History:
  v0.1 - 2025-10-20: Initial outline
  v0.2 - 2025-10-22: Roadmap FI-Health added
  v0.3 - 2025-10-24: Free Intelligence integration detailed
  v1.0 - 2025-10-25: Complete LLD for stakeholder review

Distribution:
  - Free Intelligence core team
  - Aurity engineering team
  - Product management
  - Executive stakeholders

Next Review: 2025-11-15 (post-pilot feedback)

Contact:
  Technical Lead: [email]
  Product Owner: [email]
  FI Partnership: [email]
```

---

**END OF DOCUMENT**

This Low-Level Design document provides the complete technical foundation for Aurity's implementation. It bridges the strategic vision with executable architecture, enabling both internal development and collaboration with Free Intelligence experts.

The roadmap's phased approach ensures revenue generation from Day 1 while building toward full clinical capability, all anchored in the principle of data sovereignty through on-premise Free Intelligence deployment.
