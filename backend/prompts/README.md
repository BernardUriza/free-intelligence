# Free Intelligence - Prompt Presets System

**Sistema dual de presets para prompt engineering en backend**

---

## 🎯 Arquitectura de Presets

Tienes **DOS sistemas** de presets, cada uno con propósito específico:

### 1️⃣ PersonaManager (Conversaciones Interactivas)

**Ubicación:** `config/personas/*.yaml`
**Loader:** `backend/services/llm/persona_manager.py`
**Uso:** Conversaciones del doctor con Free Intelligence

| Persona | Temperatura | Propósito |
|---------|-------------|-----------|
| `onboarding_guide` | 0.8 | Presentación inicial de FI (obsesiva, empática, filosa) |
| `soap_editor` | 0.3 | Editor interactivo de notas SOAP (preciso, estructurado) |
| `clinical_advisor` | 0.5 | Asesoramiento clínico basado en evidencia |
| `general_assistant` | 0.7 | Asistente general médico |

**Características especiales:**
- Ajuste dinámico de response_mode (`concise` | `explanatory`)
- System prompts con personalidad definida
- Optimizado para streaming de respuestas

---

### 2️⃣ PresetLoader (Tareas Automatizadas)

**Ubicación:** `backend/prompts/*.yaml`
**Loader:** `backend/schemas/preset_loader.py`
**Uso:** Workflows batch sin interacción humana

| Preset | Temperatura | Workflow |
|--------|-------------|----------|
| `intake_coach` | 0.7 | Triage de pacientes (recolección de datos) |
| `diarization_analyst` | 0.2 | Clasificación de speakers (doctor/patient/other) |
| `soap_generator` | 0.3 | Generación automática de notas SOAP |
| `corpus_search` | 0.4 | Búsqueda y análisis de corpus HDF5 |
| `emotion_analyzer` | 0.4 | Detección de estado emocional del paciente |

**Características especiales:**
- JSON Schema validation (output garantizado)
- LRU caching con TTL configurable
- Few-shot examples (mejora precisión)
- Budget controls (tokens/hour, requests/hour)
- CLI tool: `python -m backend.schemas.preset_loader list`

---

## 📋 Tabla Comparativa

| Característica | PersonaManager | PresetLoader |
|----------------|----------------|--------------|
| **Contexto** | Doctor chatea con FI | Tareas batch automatizadas |
| **Interacción** | Streaming | Request/Response |
| **Response modes** | ✅ (concise/explanatory) | ❌ |
| **JSON Schema** | ❌ | ✅ |
| **Few-shot examples** | ❌ | ✅ |
| **Budget controls** | ❌ | ✅ |
| **Caching** | ❌ | ✅ (LRU + TTL) |
| **Validación output** | Manual | Automática (jsonschema) |

---

## 🚀 Cómo Usar los Presets

### PersonaManager (Conversaciones)

```python
from backend.services.llm.persona_manager import PersonaManager

manager = PersonaManager()

# Cargar persona
config = manager.get_persona("clinical_advisor")

# Construir prompt con contexto
system_prompt = manager.build_system_prompt(
    persona="clinical_advisor",
    context={
        "response_mode": "concise",  # o "explanatory"
        "doctor_name": "Dr. Uriza"
    }
)

# Usar en llamada LLM
response = llm_client.chat(
    system_prompt=system_prompt,
    user_message="¿Qué diagnostico diferencial consideras?",
    temperature=config.temperature,
    max_tokens=config.max_tokens
)
```

### PresetLoader (Workflows)

```python
from backend.schemas.preset_loader import get_preset_loader

loader = get_preset_loader()

# Cargar preset
preset = loader.load_preset("diarization_analyst")

# Construir prompt con examples (few-shot)
messages = [
    {"role": "system", "content": preset.system_prompt}
]

# Agregar examples
for example in preset.examples:
    messages.append({"role": "user", "content": example["input"]})
    messages.append({"role": "assistant", "content": str(example["output"])})

# Agregar actual user input
messages.append({"role": "user", "content": transcription_text})

# Llamar LLM
response = llm_client.chat(
    messages=messages,
    temperature=preset.temperature,
    max_tokens=preset.max_tokens
)

# Validar output contra schema
if preset.validation_enabled:
    schema = loader.load_schema(preset.output_schema_path)
    loader.validate_output(response, schema)  # Raises if invalid
```

---

## 🔍 CLI Tool (PresetLoader)

```bash
# Listar todos los presets disponibles
python -m backend.schemas.preset_loader list

# Ver detalles de un preset
python -m backend.schemas.preset_loader load diarization_analyst

# Validar output contra schema
python -m backend.schemas.preset_loader validate soap_generator output.json
```

---

## 📝 Estructura de un Preset (YAML)

### Formato PersonaManager

```yaml
persona: "clinical_advisor"
description: "Asesor clínico basado en evidencia"
temperature: 0.5
max_tokens: 1024

system_prompt: |
  You are a clinical decision support AI assistant.

  Your role:
  - Provide evidence-based clinical guidance
  - Reference medical literature when possible
  ...
```

### Formato PresetLoader

```yaml
preset_id: "diarization_analyst"
version: "1.0.0"
description: "Speaker classification for medical consultations"

system_prompt: |
  You are a medical conversation diarization specialist...

llm:
  provider: "azure"
  model: "gpt-4"
  temperature: 0.2
  max_tokens: 2048
  stream: false

validation:
  output_schema: "backend/schemas/diarization.schema.json"
  enabled: true
  strict: true

cache:
  enabled: true
  ttl_seconds: 7200
  key_fields: ["prompt", "model"]

examples:
  - input: "Buenos días, ¿cómo se siente?"
    output:
      speaker: "DOCTOR"
      confidence: 0.95

metadata:
  task_type: "DIARIZATION"
  avg_tokens_per_call: 1500
```

---

## 🎨 Patrones de redux-claude Aplicados

### 1. Especialización por Tarea

Cada preset = 1 tarea específica (inspirado en los 13 agents de redux-claude)

```
redux-claude:          Free Intelligence:
- PatientQueryAgent  → corpus_search preset
- SOAPGenerationAgent → soap_generator preset
- DiarizationAgent   → diarization_analyst preset
- EmotionAgent       → emotion_analyzer preset
```

### 2. Few-Shot Learning

Examples en cada preset mejoran precisión (como redux-claude usa ejemplos históricos)

```yaml
examples:
  - input: "Me duele la cabeza"
    output: {"speaker": "PATIENT", "confidence": 0.92}
```

### 3. Output Validation

JSON Schema garantiza estructura (redux-claude valida con TypeScript types)

```python
loader.validate_output(response, schema)  # Raises if invalid
```

### 4. Caching Inteligente

Cache por preset + parámetros (redux-claude cachea por estado Redux)

```yaml
cache:
  key_fields: ["prompt", "model", "temperature"]
  ttl_seconds: 7200
```

### 5. Metadata-Driven

Configuración como código, no hardcoded (redux-claude usa config objects)

---

## 🧩 Cuándo Crear un Nuevo Preset

**PersonaManager (Nueva Persona):**
- Necesitas un nuevo "modo" conversacional del asistente
- Diferente tono/estilo para contextos específicos
- Ejemplo: `emergency_assistant` para consultas urgentes

**PresetLoader (Nuevo Workflow):**
- Nueva tarea automatizada sin interacción humana
- Requiere JSON Schema validation
- Beneficio de caching (tarea repetitiva)
- Ejemplo: `prescription_formatter` para estandarizar recetas

---

## 📚 Presets Recomendados para Crear (Future)

1. **transcription_qa.yaml** - Quality assurance de transcripciones
2. **diagnosis_suggester.yaml** - Sugerencias de diagnóstico diferencial
3. **medication_checker.yaml** - Validación de interacciones medicamentosas
4. **lab_interpreter.yaml** - Interpretación de resultados de laboratorio
5. **referral_generator.yaml** - Generación automática de referrals
6. **icd10_coder.yaml** - Codificación automática ICD-10

---

## 🔒 Consideraciones de Seguridad

1. **PHI Protection:**
   - Presets NO deben incluir datos de pacientes en examples
   - Output schemas NO permiten campos identificables
   - Caching solo por contenido médico, NO por paciente

2. **Validation Strict Mode:**
   - Siempre usar `strict: true` para workflows críticos (SOAP, prescriptions)
   - Prevent hallucinations con JSON Schema

3. **Budget Controls:**
   - `max_tokens_per_hour` previene abuso
   - `max_requests_per_hour` limita costos

---

## 📖 Documentación Relacionada

- `backend/schemas/preset_loader.py` - Código del loader
- `backend/services/llm/persona_manager.py` - Código del manager
- `backend/prompts/*.yaml` - Presets de workflows
- `config/personas/*.yaml` - Presets de conversación

---

**Inspirado por:** [redux-claude](https://github.com/BernardUriza/redux-claude)
**Creado:** 2025-11-20
**Versión:** 1.0.0
