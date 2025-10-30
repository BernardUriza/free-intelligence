# Free Intelligence Cold - Video Script (90 segundos)

**Target**: Decision makers (hospital/clinic owners, medical directors)
**Goal**: Show value proposition + demo funcionando en ≤90s
**Format**: Screen recording + voiceover

---

## 🎬 Script Timeline

### **0:00-0:10 (10s) - Hook + Problem**
**[Screen: Logo FI + estadística]**

> "En México, el 40% del tiempo de consulta se va en documentación. No en atender al paciente."

**Visual**: Reloj girando + doctor escribiendo en papel

---

### **0:10-0:25 (15s) - Solution Intro**
**[Screen: Arquitectura FI-Cold diagram]**

> "Free Intelligence Cold es un sistema de consultas médicas asistidas por IA que opera 100% en su infraestructura local."

**Visual**: Diagrama LAN con datos circulando dentro del hospital, NO hacia internet

> "Sus datos médicos NUNCA salen de su red. Sin nube, sin suscripciones, sin riesgos."

---

### **0:25-0:45 (20s) - Demo: IntakeCoach**
**[Screen: AURITY UI en localhost:9000]**

> "Veamos IntakeCoach en acción. Un paciente llega con dolor de pecho."

**Visual**: Typing en pantalla

- **User**: "Tengo dolor en el pecho desde hace 2 horas"
- **IntakeCoach**: "Entiendo, esto es importante. ¿El dolor se extiende al brazo o mandíbula? En escala 1-10, ¿qué tan fuerte es?"
- **User**: "Sí, al brazo izquierdo. 8 de 10."

> "El sistema detecta síntoma crítico y clasifica como URGENCIA ALTA automáticamente."

**Visual**: Badge rojo "CRITICAL" aparece en pantalla

---

### **0:45-1:05 (20s) - Demo: SOAP Note Generation**
**[Screen: SOAP note generada automáticamente]**

> "En segundos, genera una nota SOAP completa, NOM-004-SSA3-2012 compliant."

**Visual**: Nota SOAP desplegándose

```
SOAP Note - Paciente Demo
S: Dolor torácico 8/10, irradiado a brazo izquierdo, 2h evolución
O: Paciente alerta, sudoroso, signos vitales pendientes
A: Sospecha síndrome coronario agudo
P: Valoración inmediata, ECG, laboratorios urgentes
```

> "El médico valida, ajusta si necesario, y confirma. Documentación lista en 2 minutos, no 8."

---

### **1:05-1:20 (15s) - ROI + Value Prop**
**[Screen: Números impact]**

> "Para una clínica con 5 consultorios:"
- ✅ +40 pacientes/día sin contratar más médicos
- ✅ $245,000 MXN inversión inicial, o $2,900/mes leasing
- ✅ ROI en 8-10 meses

**Visual**: Gráfica ascendente "Pacientes atendidos"

---

### **1:20-1:30 (10s) - Call to Action**
**[Screen: Contacto + oferta]**

> "Primeros 5 pilotos: 20% descuento + hardware upgrade gratis."

**Visual**: Logo FI + QR code para agendar demo

> "Free Intelligence Cold. Inteligencia sin comprometer privacidad."

**Text overlay**:
- 📧 bernard.uriza@free-intelligence.health
- 🌐 [Por definir]
- 📅 Agenda tu demo: [QR code]

---

## 🎥 Production Notes

### Visual Requirements
1. **Screen recordings**:
   - Docker compose up (sped up 4x)
   - Browser: localhost:9000 (AURITY UI)
   - IntakeCoach conversation (real-time typing animation)
   - SOAP note generation (smooth reveal animation)

2. **Graphics**:
   - FI-Cold logo (animated intro)
   - Arquitectura diagram (simple, 3 boxes: LAN, FI Backend, AURITY Frontend)
   - Stats overlay (pacientes/día, ROI timeline)
   - QR code para contact

3. **Transitions**:
   - Fade in/out (0.5s max)
   - No fancy effects (professional, medical tone)

### Audio Requirements
1. **Voiceover**:
   - Voz profesional, neutral (no dramatic)
   - Ritmo: 120-140 palabras/minuto
   - Tono: Confident but not salesy

2. **Background music** (optional):
   - Subtle, ambient (no lyrics)
   - Volume: -20dB (barely audible)
   - Royalty-free (Epidemic Sound, Artlist)

### Technical Specs
- **Resolution**: 1920x1080 (Full HD)
- **Frame rate**: 30fps
- **Format**: MP4 (H.264 codec)
- **File size**: ≤50MB (for email distribution)
- **Subtitles**: Spanish (SRT file included)

---

## 📝 Alternative Versions

### Version A: Tech-focused (for IT decision makers)
- More emphasis on architecture (HDF5, event sourcing, SHA256 audit)
- Less clinical workflow, more infrastructure security
- Duration: 90s same

### Version B: ROI-focused (for CFOs/administrators)
- Start with problem: "¿Cuánto le cuesta a su hospital documentar cada consulta?"
- Show cost breakdown: time = money
- End with payback period calculation
- Duration: 60s (shorter, punchier)

### Version C: Compliance-focused (for legal/risk management)
- Emphasis on NOM-004, audit trail, non-repudiation
- Show SHA256 hashing, export manifests
- Address HIPAA readiness
- Duration: 90s same

---

## 🎯 Distribution Strategy

### Primary channels:
1. **Email outreach**: Attachment in first cold email to decision makers
2. **LinkedIn**: Pinned post on Bernard's profile
3. **WhatsApp**: Send directly to warm leads
4. **Demo meetings**: Show live before talking pricing

### Analytics tracking:
- Views: Vimeo embed with analytics
- Engagement: Track drop-off points (if >50% drop before 60s, re-edit)
- Conversions: How many viewers book demo

---

## ✅ Completion Checklist

Before finalizing video:
- [ ] Script reviewed by medical professional (validate terminology)
- [ ] Demo data is realistic but anonymized (no real PHI)
- [ ] All URLs/emails are correct
- [ ] QR code works (test on 3 different phones)
- [ ] Subtitles sync correctly (±0.5s tolerance)
- [ ] File size <50MB
- [ ] Exported in 3 formats: MP4 (email), MOV (high quality), WebM (web)
- [ ] Backup on 2 locations (NAS + cloud)

---

**Status**: Script ready for production
**Next step**: Record screen demos + voiceover
**ETA**: 2-3 hours production time
