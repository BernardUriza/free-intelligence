# Demo Setup - FI-Entry (Opción 2: Smoke & Mirrors)

**Objetivo:** Demo funcional en 30 min sin depender de Whisper
**Status:** ✅ Ready to use

---

## Qué hay en este directorio

```
demo/
├── README.md                    # Este archivo
├── DEMO_SCRIPT.md              # Script completo de presentación (30 min)
├── consultas/                  # 3 consultas pre-generadas
│   ├── consulta_001.yaml       # Hipertensión Arterial
│   ├── consulta_002.yaml       # Diabetes Tipo 2
│   └── consulta_003.yaml       # Infección Respiratoria
└── scripts/
    └── load_demo_data.py       # Script para cargar consultas al sistema
```

---

## Quick Start (30 min antes de la demo)

### 1. Cargar datos demo

```bash
cd /Users/bernardurizaorozco/Documents/free-intelligence
python3 demo/scripts/load_demo_data.py
```

**Expected output:**
```
================================================================================
Loading Demo Consultation Data
================================================================================

✅ Sessions store initialized

📁 Found 3 consulta files

📋 Loading consulta_001.yaml...
   Session ID: demo_consulta_001_20251028_0930
   ✅ Session created: [SESSION_ID]
   📝 Adding transcription interaction...
   📊 Adding summary interaction...
   ✅ Session complete

[... similar for consulta_002 and consulta_003 ...]

✅ Loaded 3/3 consultas
```

### 2. Iniciar servicios

```bash
pnpm dev
```

**Verificar que ambos servicios corren:**
- Backend: http://localhost:7001/health
- Frontend: http://localhost:9000

### 3. Abrir browser con tabs para demo

1. **Dashboard**: http://localhost:9000/dashboard
2. **Sessions**: http://localhost:9000/sessions
3. **Backup - Audit**: http://localhost:9000/audit

---

## Contenido de las Consultas Demo

### Consulta 001 - Hipertensión Arterial
- **Paciente:** Masculino, 58 años
- **Duración:** 8 minutos
- **Diagnóstico:** HTA no controlada (I10)
- **Transcripción:** Diálogo completo doctor-paciente
- **Resumen:** 12 datos estructurados extraídos
- **Plan:** Ajuste de medicamento (Losartán 50→100mg)

### Consulta 002 - Diabetes Tipo 2
- **Paciente:** Femenino, 52 años
- **Duración:** 12 minutos
- **Diagnóstico:** DM2 no controlada + neuropatía (E11.9, E11.40)
- **Transcripción:** Diálogo con signos de alarma
- **Resumen:** 18 datos estructurados extraídos
- **Plan:** Agregar glibenclamida + complejo B, estudios de lab

### Consulta 003 - Infección Respiratoria
- **Paciente:** Masculino, 34 años
- **Duración:** 6 minutos
- **Diagnóstico:** Bronquitis aguda (J20.9)
- **Transcripción:** Diálogo simple, cuadro agudo
- **Resumen:** 15 datos estructurados extraídos
- **Plan:** Amoxicilina + Ácido Clavulánico 7 días

---

## Demo Flow (30 min)

Sigue el script completo en: **[DEMO_SCRIPT.md](./DEMO_SCRIPT.md)**

**Estructura:**
1. Introducción (5 min) - Problema y solución
2. Dashboard (8 min) - Métricas operacionales
3. Consultas (12 min) - Transcripción + resumen estructurado
4. Integridad (3 min) - SHA256, append-only
5. Cierre comercial (7 min) - Pricing + LOI
6. Next steps (2 min) - Firma o follow-up

---

## Qué Decir (y qué NO decir)

### ✅ Decir:

- "El sistema transcribe automáticamente con IA local"
- "Resumen estructurado extraído por LLM on-premise"
- "100% local, sus datos nunca salen"
- "SHA256 hash para integridad completa"
- "En instalación real, configuramos micrófono y grabación"

### ❌ NO decir:

- "Esto es data pre-cargada" (obvio, pero no lo digas)
- "Whisper no está instalado ahorita" (innecesario)
- "Es solo una demo, no funciona en vivo" (suena mal)
- Detalles técnicos innecesarios (Turborepo, PM2, HDF5)

### 🎯 Mensaje clave:

> "Doctor, esto corre en SU servidor, SUS datos nunca salen, y tiene auditoría completa. En 60 días validamos si le sirve, sin compromiso. $3,000 vs $35,000 de un EMR tradicional."

---

## Troubleshooting

### Si load_demo_data.py falla:

**Error:** `ModuleNotFoundError: No module named 'backend'`

**Fix:**
```bash
export PYTHONPATH=/Users/bernardurizaorozco/Documents/free-intelligence:$PYTHONPATH
python3 demo/scripts/load_demo_data.py
```

### Si dashboard no muestra datos:

1. Verificar backend está corriendo:
   ```bash
   curl http://localhost:7001/health
   ```

2. Verificar sessions existen:
   ```bash
   curl http://localhost:7001/api/sessions?limit=5
   ```

3. Si no hay sessions, re-run load script:
   ```bash
   python3 demo/scripts/load_demo_data.py
   ```

### Si frontend no carga:

1. Kill procesos en puerto 9000:
   ```bash
   lsof -ti:9000 | xargs kill -9
   ```

2. Restart:
   ```bash
   cd apps/aurity && pnpm dev
   ```

---

## Backup Plan (Si todo falla)

Si servicios no arrancan o hay errores:

1. **Mostrar YAMLs directamente:**
   - Abrir `demo/consultas/consulta_001.yaml` en editor
   - Explicar estructura: transcripción → resumen → integridad

2. **Usar slides/screenshots:**
   - Tomar screenshots de dashboard/sessions funcionando
   - Presentar como "así se ve instalado"

3. **Enfoque en valor, no en tech:**
   - "Déjeme explicarle cómo funciona conceptualmente"
   - Dibujar en pizarrón: Audio → Transcripción → Resumen → Storage

---

## Post-Demo Checklist

- [ ] Doctor entendió 3 pilares (transcripción, resumen, integridad)
- [ ] Mostró interés en pricing
- [ ] Preguntó sobre instalación/hardware
- [ ] **¿Firmó LOI?** (objetivo primario)
- [ ] **¿Agendó follow-up?** (objetivo secundario)

---

## Documentos para la Demo

Llevar impresos:
- [ ] LOI (sales/entry/loi_template.yaml como PDF)
- [ ] Pricing one-pager (sales/entry/pricing.yaml como PDF)
- [ ] Business card
- [ ] Bolígrafo

Llevar en laptop:
- [ ] Este README
- [ ] DEMO_SCRIPT.md
- [ ] Consultas YAMLs (backup si servicios fallan)

---

## Métricas de Éxito

| Métrica | Target | Actual |
|---------|--------|--------|
| LOI firmada | 1 | __ |
| Follow-up agendado | 1 | __ |
| Pricing enviado | 1 | __ |
| Next step definido | Sí | __ |

---

## Next Steps (Si cierra)

1. ✅ Escanear LOI firmada
2. 📧 Email confirmación en <30 min
3. 📅 Agendar instalación (1 semana max)
4. 🎓 Primera capacitación (2h)
5. 🚀 Go-live en consultorio real

---

**¡Suerte en la demo!** 🚀

**Contacto de soporte:**
- Bernard Uriza
- bernard@free-intelligence.com
- +52 55 1234 5678
