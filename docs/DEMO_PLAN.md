# Demo Plan - Doctor Consulta (Próxima Semana)

**Cliente:** Doctor con poco tiempo
**Necesidad:** Transcribir consultas + Resumen + Almacenamiento íntegro
**Fecha Demo:** Próxima semana
**Status Actual:** ⚠️ BLOQUEADO - Whisper no instalado

---

## ✅ Lo que SÍ tenemos funcionando

### Backend APIs (puerto 7001)
- ✅ POST /api/transcribe - Endpoint existe y está montado
- ✅ Audio storage (data/audio_sessions/)
- ✅ SHA256 manifest para integridad
- ✅ Graceful degradation si Whisper no disponible
- ✅ Timeline API para ver sesiones
- ✅ Export API con verification

### Frontend (puerto 9000)
- ✅ Dashboard con KPIs
- ✅ Sessions list
- ✅ Timeline viewer
- ✅ Export modal
- ✅ Audit log

### Storage
- ✅ HDF5 corpus (storage/corpus.h5) - append-only
- ✅ Sessions manifest (JSONL)
- ✅ Audio buffers con SHA256

---

## ❌ Lo que FALTA para la demo

### Crítico (Bloqueante)
1. **Whisper NO está instalado**
   - Error: `ModuleNotFoundError: No module named 'whisper'`
   - Fix: `pip install openai-whisper`
   - Modelo recomendado: `base` (74MB, balance speed/accuracy)
   - Alternativa: `tiny` (39MB, más rápido) para demo

2. **No hay resumen automático de transcripción**
   - Transcribe API solo devuelve texto plano
   - Falta: POST /api/summarize o integración LLM
   - Opciones:
     - LLM local (Ollama + qwen2:7b) ← Ya tenemos esto
     - Claude API (blocked por egress policy)
     - Simple bullet points extraction

3. **UI para grabar audio desde browser**
   - Frontend tiene /triage pero sin grabación
   - Falta: MediaRecorder API + botón "Grabar consulta"
   - Workaround demo: Subir archivo .wav pre-grabado

### Nice-to-Have (No bloqueante)
4. **Visualización de transcripción + resumen**
   - Mostrar transcripción raw + resumen estructurado
   - Timeline viewer existe pero no muestra audio/texto

5. **Export de consulta completa**
   - Audio + Transcripción + Resumen en 1 ZIP
   - Export API existe pero no agrupa estos 3

---

## 🚀 Plan de Acción (Orden de Prioridad)

### Día 1-2: Desbloquear Whisper
```bash
# Instalar Whisper
pip install openai-whisper

# Descargar modelo base (74MB)
python3 -c "import whisper; whisper.load_model('base')"

# Test básico
echo "Hola doctor" | espeak -w test.wav --stdout
curl -X POST http://localhost:7001/api/transcribe \
  -F "audio=@test.wav" \
  -F "session_id=demo_20251030"
```

### Día 3: Integrar Resumen (LLM local)
```python
# Crear backend/api/summarize.py
POST /api/summarize
Input: {"text": "transcripción larga..."}
Output: {
  "summary": {
    "motivo_consulta": "dolor de cabeza",
    "sintomas": ["cefalea", "náuseas"],
    "diagnostico_preliminar": "migraña",
    "plan": "ibuprofeno 400mg c/8h"
  }
}

# Usar Ollama local (ya configurado)
Provider: ollama
Model: qwen2:7b
Prompt: "Resume esta consulta médica en 4 categorías..."
```

### Día 4: UI Grabación (o Workaround)
**Opción A (Ideal):** MediaRecorder API
- Botón "Grabar Consulta" en /triage
- 60s max grabación
- Upload automático a /api/transcribe

**Opción B (Workaround Demo):**
- Grabar audio con Voice Memos (macOS/iOS)
- Exportar .wav
- Subir manualmente en /triage
- Suficiente para demo

### Día 5: End-to-End Test
```bash
# Script de demo completo
./scripts/demo_consulta.sh

# Flujo:
1. Grabar audio (60s consulta simulada)
2. POST /api/transcribe → transcripción
3. POST /api/summarize → resumen estructurado
4. Guardar en corpus.h5 (append-only)
5. Mostrar en dashboard + timeline
6. Export con SHA256 verification
```

### Día 6-7: Preparación Demo
- Datos demo realistas (3-5 consultas)
- Script de presentación
- Backup plan si algo falla
- Pricing + LOI listos para cerrar

---

## 📋 Checklist Demo (Día D)

### Pre-Demo (30 min antes)
- [ ] Backend corriendo (pnpm dev)
- [ ] Whisper modelo cargado (python3 -c "import whisper")
- [ ] Ollama corriendo (ollama list | grep qwen2)
- [ ] Frontend accessible (http://localhost:9000)
- [ ] Audio de prueba grabado (3 consultas demo)

### Durante Demo (30-45 min)
1. **Intro (5 min)**
   - [ ] Mostrar problema: docs fragmentados
   - [ ] Propuesta: FI-Entry on-premise

2. **Demo Live (25 min)**
   - [ ] Grabar consulta (o subir .wav)
   - [ ] Mostrar transcripción en tiempo real
   - [ ] Mostrar resumen estructurado
   - [ ] Dashboard con métricas
   - [ ] Export con SHA256 (integridad)

3. **Q&A + Cierre (10 min)**
   - [ ] Pricing: $3k piloto 60 días
   - [ ] Hardware: su DELL existente OK
   - [ ] Privacidad: 100% local, sin cloud
   - [ ] Next step: firmar LOI esta semana

### Post-Demo
- [ ] Enviar LOI por email
- [ ] Follow-up en 48h
- [ ] Agendar instalación si firma

---

## 🎯 Objetivo de la Demo

**Demostrar en 30 minutos:**
1. ✅ Audio → Transcripción funciona (Whisper local)
2. ✅ Transcripción → Resumen automático (LLM local)
3. ✅ Almacenamiento íntegro (HDF5 + SHA256)
4. ✅ Dashboard con métricas
5. ✅ Export para auditoría

**Mensaje clave:**
"Doctor, esto corre en SU servidor, SUS datos nunca salen, y tiene auditoría completa. En 60 días validamos si le sirve, sin compromiso."

---

## 🚨 Riesgos & Mitigación

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Whisper falla en demo | Media | Alto | Tener transcripción pre-generada como backup |
| Audio tiene ruido | Alta | Medio | Grabar en ambiente silencioso, probar antes |
| LLM resumen es malo | Media | Medio | Tener prompt bien tuneado, mostrar raw text también |
| Internet falla en demo | Baja | Bajo | Demo es 100% local (LAN-only) |
| Doctor no firma LOI | Alta | Alto | Tener pricing claro, offer irresistible ($3k vs $30k EMR) |

---

## 📝 Próximos Pasos (AHORA)

1. **Instalar Whisper** (15 min)
2. **Crear POST /api/summarize** (2h)
3. **Script demo end-to-end** (1h)
4. **Grabar 3 consultas demo** (1h)
5. **Ensayar demo** (30 min)

**Total estimado: 5h de trabajo**

**Deadline: 3 días antes de la demo** (buffer para bugs)
