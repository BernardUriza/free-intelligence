# Free Intelligence — Baseline de Probabilidad y Metas GTM

**Version**: 1.0
**Fecha**: Octubre 2025
**Owner**: Bernard Uriza Orozco
**Sprint**: SPR-2025W44

---

## 🎯 Baseline de Probabilidad

### Modelo Probabilístico

Usamos un modelo bayesiano informal que combina:
1. **Factores técnicos** (madurez producto, diferenciación, compliance)
2. **Factores comerciales** (leads, horas ventas, canales)
3. **Factores de mercado** (timing, competencia, urgencia cliente)

**Scoring actual**: **3.23/5.0** (ver breakdown abajo)

### Probabilidades Base (Sin Palancas)

| Objetivo | Timeline | Probabilidad | Confianza |
|----------|----------|--------------|-----------|
| **1 piloto firmado** | ≤12 meses | **65%** | ±10% |
| **5 clínicas operando** | ≤36 meses | **45%** | ±15% |
| **5 clínicas operando** | ≤60 meses | **75%** | ±10% |

**Interpretación**:
- **1 piloto ≤12m (65%)**: Alta probabilidad dado producto funcional + demo + one-pager
- **5 clínicas ≤36m (45%)**: Moderada probabilidad, depende de referencias y expansión orgánica
- **5 clínicas ≤60m (75%)**: Alta probabilidad con suficiente tiempo para iteración

### Factores del Scoring (3.23/5.0)

| Factor | Peso | Score | Contribución | Notas |
|--------|------|-------|--------------|-------|
| **Madurez producto** | 15% | 3.5/5 | 0.53 | MVP funcional, falta UX polish |
| **Diferenciación** | 12% | 4.5/5 | 0.54 | 100% local es único en México |
| **Compliance/Seguridad** | 10% | 4.0/5 | 0.40 | NOM-004, append-only, audit trail |
| **Demo funcionando** | 10% | 4.0/5 | 0.40 | Docker + one-pager listo |
| **Leads activos** | 15% | 1.0/5 | 0.15 | ⚠️ **CUELLO DE BOTELLA** |
| **Horas ventas/sem** | 10% | 2.0/5 | 0.20 | 8h/sem insuficiente (target: 20h) |
| **Pricing definido** | 8% | 4.0/5 | 0.32 | Compra + leasing estructurado |
| **Canales activados** | 8% | 2.0/5 | 0.16 | Solo outreach directo |
| **Referencias** | 7% | 1.0/5 | 0.07 | Sin pilotos aún |
| **Urgencia mercado** | 5% | 3.5/5 | 0.18 | Documentación es problema real |
| **TOTAL** | **100%** | — | **3.23/5.0** | **Scoring actual** |

### Cuellos de Botella Identificados

1. **Leads (1.0/5)**: Solo 1 lead activo, necesitamos 10+ para funnel saludable
2. **Horas ventas (2.0/5)**: 8h/sem vs 20h/sem óptimo = -60% capacidad

---

## 📈 Palancas de Crecimiento

### Palanca 1: Leads (1 → 10 leads)

**Impacto**: 1 piloto ≤12m: **65% → 80%** (+15pp)

**Justificación**:
- Con 10 leads de calidad (dueños/decisores):
  - Conversión 30% = 3 pilotos en pipeline
  - Probabilidad de al menos 1 cierre ≤12m aumenta significativamente
- Reduce dependencia de un solo lead (diversificación)

**Implementación**: Ver FI-GTM-MILE-001

### Palanca 2: Horas Ventas (8h → 20h/sem)

**Impacto**: Time-to-acquisition: **12m → 8m** (-33%)

**Justificación**:
- 8h/sem = 1 reunión/sem + follow-ups limitados
- 20h/sem = 3 reuniones/sem + email campaigns + demos
- Reduce TTA (Time To Acquisition) en 3-4 meses

**Implementación**: Ver FI-GTM-MILE-002 (vendedor fraccional)

### Palanca 3: Oferta FI-Cold (Sin PHI)

**Impacto**: Ciclo de venta: **6-9 meses → 3-4 meses** (-50%)

**Justificación**:
- Sin PHI = Sin certificaciones NOM-024/HIPAA en fase 1
- LOI en 60 días vs 120 días con compliance completo
- Menos objeciones legales/IT en negociación

**Implementación**: Ver FI-GTM-STRAT-002

### Impacto Combinado de Palancas

| Palancas activadas | 1 piloto ≤12m | 5 clínicas ≤36m | Scoring |
|--------------------|---------------|-----------------|---------|
| **Ninguna (baseline)** | 65% | 45% | 3.23/5 |
| **Palanca 1 (leads)** | 80% | 55% | 3.53/5 |
| **Palanca 1+2 (leads+ventas)** | 85% | 65% | 3.83/5 |
| **Palanca 1+2+3 (todas)** | 90% | 75% | 4.23/5 |

---

## 🎯 Metas Trimestrales (OKRs)

### Q1 2026 (Ene-Mar): Activación

**Objetivo**: Establecer baseline comercial

**Key Results**:
1. ✅ 10 leads calientes identificados (dueños/decisores)
2. ✅ 5 demos agendadas (conversión 50%)
3. ✅ 2 LOIs firmados (conversión demo → LOI 40%)
4. ✅ 1 piloto iniciado (conversión LOI → piloto 50%)

**Métricas**:
- Leads contacted: 30+ (outreach)
- Leads qualified: 10+ (target decision makers)
- Demos completed: 5 (conversión 50%)
- LOIs signed: 2 (conversión 40%)
- Pilots started: 1 (conversión 50%)

### Q2 2026 (Abr-Jun): Validación

**Objetivo**: Completar primer piloto + referencias

**Key Results**:
1. ✅ 1 piloto completado (60 días operación)
2. ✅ Case study documentado (ROI, métricas, testimonial)
3. ✅ 2 referencias obtenidas del piloto
4. ✅ 2 pilotos adicionales iniciados

**Métricas**:
- Pilots completed: 1
- Case studies: 1 (video + PDF)
- Referrals: 2 (warm intros)
- Pilots in progress: 2

### Q3 2026 (Jul-Sep): Escalamiento

**Objetivo**: Múltiples pilotos + primera conversión a producción

**Key Results**:
1. ✅ 1 piloto → producción (primera clínica pagando)
2. ✅ 3 pilotos completados (total acumulado: 4)
3. ✅ 20 leads en pipeline (funnel saludable)
4. ✅ Vendedor fraccional contratado (Palanca 2)

**Métricas**:
- Customers (production): 1
- Pilots completed (cumulative): 4
- Active pipeline: 20 leads
- Sales capacity: 20h/sem (was 8h/sem)

### Q4 2026 (Oct-Dic): Crecimiento

**Objetivo**: 2 clínicas en producción + pipeline robusto

**Key Results**:
1. ✅ 2 clínicas en producción (total: 2)
2. ✅ 5 pilotos completados (total acumulado: 9)
3. ✅ MRR $5,800 MXN (2 clínicas × $2,900/mes leasing)
4. ✅ 30 leads en pipeline (growth)

**Métricas**:
- Customers (production): 2
- Pilots completed (cumulative): 9
- MRR: $5,800 MXN
- Active pipeline: 30 leads

---

## 📊 Métricas de Éxito

### Métricas Primarias (North Star)

| Métrica | Q1 | Q2 | Q3 | Q4 | 2026 Total |
|---------|----|----|----|----|------------|
| **Clínicas en producción** | 0 | 0 | 1 | 2 | **2** |
| **Pilotos completados (acum)** | 1 | 1 | 4 | 9 | **9** |
| **MRR (leasing)** | $0 | $0 | $2,900 | $5,800 | **$5,800** |
| **Leads en pipeline** | 10 | 10 | 20 | 30 | **30** |

### Métricas Secundarias

| Métrica | Target 2026 |
|---------|-------------|
| **Demos realizados** | 15+ |
| **Conversión demo → LOI** | 40% |
| **Conversión LOI → piloto** | 50% |
| **Conversión piloto → producción** | 20% |
| **Tiempo promedio LOI → producción** | 120 días |

### Métricas de Calidad

| Métrica | Target |
|---------|--------|
| **NPS (Net Promoter Score)** | 50+ |
| **Churn rate (año 1)** | <10% |
| **Customer ROI** | 8-10 meses payback |
| **Uptime** | >99% |

---

## 🚨 Señales de Alerta

### Red Flags (Revisar estrategia)

- ❌ 0 LOIs firmados en Q1 → Problema con producto/pricing/demo
- ❌ >6 meses para completar piloto → Problemas de implementación
- ❌ <30% conversión demo → LOI → Problema con value prop
- ❌ Churn >20% año 1 → Producto no resuelve problema real

### Yellow Flags (Monitorear)

- ⚠️ <5 demos en Q1 → Pipeline insuficiente
- ⚠️ Time-to-LOI >90 días → Ciclo de venta muy largo
- ⚠️ 0 referencias de pilotos → Satisfacción baja

---

## 🔄 Proceso de Revisión

### Frecuencia

- **Semanal**: Leads contacted, demos agendadas (métricas input)
- **Mensual**: LOIs, pilotos iniciados/completados (métricas output)
- **Trimestral**: OKRs review + ajuste de metas

### Responsables

- **Bernard**: Estrategia, demos técnicas, implementaciones
- **Vendedor fraccional** (Q3+): Outreach, follow-ups, cierre LOIs
- **Review board**: Bernard + advisor externo (TBD)

### Ajustes de Baseline

Baseline se revisará trimestralmente. Factores que pueden cambiar scoring:

| Factor | Trigger de cambio |
|--------|-------------------|
| **Madurez producto** | Lanzamiento features críticos (UX polish, integrations) |
| **Leads activos** | Activación de Palanca 1 (1 → 10 leads) |
| **Horas ventas** | Contratación vendedor fraccional (8h → 20h/sem) |
| **Referencias** | Primer piloto completado con case study |
| **Canales activados** | LinkedIn ads, partnerships, eventos |

---

## 📚 Referencias

### Fuentes

1. **Bitácora FI**: `claude.md` (entrada 2025-10-28 00:50)
   - Estrategia de probabilidad + palancas
   - Scoring 3.23/5 con breakdown completo

2. **One-pager FI-Cold**: `docs/sales/FI-COLD-ONE-PAGER.md`
   - Pricing, casos de uso, ROI

3. **Cards Trello**:
   - FI-GTM-MILE-001: Palanca 1 (leads)
   - FI-GTM-MILE-002: Palanca 2 (vendedor fraccional)
   - FI-GTM-STRAT-002: Palanca 3 (oferta FI-Cold)

### Supuestos Clave

1. **Producto**: MVP funcional en Q1 2026 (ya cumplido)
2. **Pricing**: Aceptable para mercado SMB México ($2,900/mes leasing)
3. **Mercado**: Problema de documentación es real y urgente
4. **Competencia**: No hay solución 100% local comparable
5. **Timing**: Post-COVID, clínicas buscan eficiencia operativa

### Riesgos

1. **Macro**: Recesión en México → presupuestos congelados
2. **Producto**: Bugs críticos en producción → churn alto
3. **Ventas**: No encontrar vendedor fraccional de calidad
4. **Legal**: Cambios regulatorios NOM-004 que requieran re-arquitectura

---

## ✅ Checklist de Entregables

- [x] Baseline de probabilidad documentado (65% 1 piloto ≤12m)
- [x] Scoring de factores (3.23/5.0 con breakdown)
- [x] Palancas identificadas (3 palancas con impacto cuantificado)
- [x] Metas trimestrales definidas (Q1-Q4 2026 con OKRs)
- [x] Métricas de éxito especificadas (primarias + secundarias)
- [x] Red/yellow flags documentados
- [ ] Link añadido a README.md (pending)

---

**Status**: Baseline completo ✅
**Próximo paso**: Publicar en README + vincular con cards de palancas
**Owner**: Bernard Uriza Orozco
**Última actualización**: 2025-10-28
