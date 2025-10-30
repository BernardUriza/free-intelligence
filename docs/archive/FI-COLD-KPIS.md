# Free Intelligence Cold — KPIs & Performance Metrics

**Version**: 1.0
**Fecha**: Octubre 2025
**Propósito**: Métricas para pilotos FI-Cold

---

## 🎯 Overview

Este documento define los **Key Performance Indicators (KPIs)** para evaluar el éxito de pilotos FI-Cold. Las métricas están organizadas en 4 categorías:

1. **Technical Performance** (sistema funcionando correctamente)
2. **User Adoption** (médicos y staff usando el sistema)
3. **Clinical Impact** (mejora en workflow médico)
4. **Data Integrity** (compliance y auditoría)

---

## 1. Technical Performance

### 1.1 Uptime

| Métrica | Target | Cálculo | Frecuencia |
|---------|--------|---------|------------|
| **System uptime** | >95% | (Tiempo activo / Tiempo total) × 100 | Diario |
| **MTTR (Mean Time To Repair)** | <4 horas | Promedio tiempo resolución incidencias críticas | Por incidencia |
| **Unplanned downtime** | <5 horas/mes | Suma de caídas no programadas | Mensual |

**Cómo se mide**:
- Monitoreo automático (health checks cada 60s)
- Logs de disponibilidad en `/logs/uptime.log`
- Dashboard: http://localhost:9000/admin/health

### 1.2 Response Time

| Métrica | Target | Cálculo | Frecuencia |
|---------|--------|---------|------------|
| **API response time** | <3 segundos | p95 de llamadas backend | Cada consulta |
| **SOAP generation time** | <5 segundos | Tiempo desde intake completo → nota generada | Por nota SOAP |
| **UI load time** | <2 segundos | Tiempo desde request → página renderizada | Por página |

**Cómo se mide**:
- Logs de backend con timestamps
- `backend/telemetry.py` captura latencias
- Reporte semanal: `/exports/weekly-performance.md`

### 1.3 Error Rate

| Métrica | Target | Cálculo | Frecuencia |
|---------|--------|---------|------------|
| **Critical errors** | 0 | Errores que impiden uso del sistema | Por sprint (60 días) |
| **Non-critical errors** | <5/semana | Errores que no bloquean funcionalidad principal | Semanal |
| **User-reported bugs** | <10/piloto | Issues reportados por usuarios | Acumulado |

**Cómo se mide**:
- Error logging automático
- Trello board para bug tracking
- Encuestas semanales a usuarios

---

## 2. User Adoption

### 2.1 Usage Frequency

| Métrica | Target | Cálculo | Frecuencia |
|---------|--------|---------|------------|
| **Daily active users (DAU)** | ≥80% | (Usuarios activos hoy / Total usuarios) × 100 | Diario |
| **Consultations per day** | ≥5 | Número de consultas registradas en sistema | Diario |
| **Repeat usage rate** | ≥90% | Usuarios que usan sistema >3 días/semana | Semanal |

**Cómo se mide**:
- Logs de sesiones en `/audit_logs/`
- User IDs únicos por día
- Dashboard: http://localhost:9000/admin/users

### 2.2 User Satisfaction

| Métrica | Target | Cálculo | Frecuencia |
|---------|--------|---------|------------|
| **Doctor satisfaction** | ≥4/5 | Promedio de encuestas de satisfacción | Semanal + final |
| **Staff satisfaction** | ≥4/5 | Promedio de encuestas de satisfacción | Semanal + final |
| **NPS (Net Promoter Score)** | ≥50 | (% Promoters - % Detractors) | Final del piloto |

**Cómo se mide**:
- Google Forms enviado viernes cada semana
- Escala 1-5 para satisfacción
- Escala 0-10 para NPS

### 2.3 Training Effectiveness

| Métrica | Target | Cálculo | Frecuencia |
|---------|--------|---------|------------|
| **Time to proficiency** | ≤2 días | Días hasta que usuario usa sistema sin ayuda | Por usuario |
| **Support requests** | <3/usuario | Preguntas de soporte después de training | Acumulado |
| **Training completion** | 100% | Usuarios que completaron training de 4h | Una vez (día 1) |

**Cómo se mide**:
- Support ticket system (email/WhatsApp)
- Attendance log de capacitación
- Self-reported proficiency survey

---

## 3. Clinical Impact

### 3.1 Time Savings

| Métrica | Target | Cálculo | Frecuencia |
|---------|--------|---------|------------|
| **Intake time saved** | ≥30% | (Tiempo antes - Tiempo después) / Tiempo antes × 100 | Mensual |
| **SOAP notes generated** | ≥30 notas | Conteo de notas generadas por sistema | Acumulado |
| **Avg time per consultation** | ≤10 min | Tiempo desde inicio intake → SOAP confirmado | Por consulta |

**Baseline (pre-FI)**:
- Intake manual: 5-8 min
- Documentación SOAP: 5-10 min
- **Total**: 10-18 min por consulta

**Target (con FI)**:
- Intake asistido: 2-3 min
- Validación SOAP: 2-3 min
- **Total**: 4-6 min por consulta
- **Ahorro**: 6-12 min (40-67%)

**Cómo se mide**:
- Timestamps en event store (CONSULTATION_STARTED → SOAP_CONFIRMED)
- Encuesta a médicos: ¿Cuánto tiempo ahorra?
- Comparativa pre/post pilot

### 3.2 Triage Accuracy

| Métrica | Target | Cálculo | Frecuencia |
|---------|--------|---------|------------|
| **Urgency classification accuracy** | ≥90% | (Clasificaciones correctas / Total) × 100 | Mensual |
| **Critical cases detected** | 100% | Widow makers, STEMIs, etc. no perdidos | Acumulado |
| **False positives (CRITICAL)** | <10% | Casos marcados CRITICAL que no lo eran | Mensual |

**Cómo se mide**:
- Médico valida clasificación de urgencia en cada caso
- Logs: `urgency_classification` vs `doctor_override`
- Reporte mensual de accuracy

### 3.3 Clinical Quality

| Métrica | Target | Cálculo | Frecuencia |
|---------|--------|---------|------------|
| **SOAP completeness** | ≥95% | Notas con todas las secciones S/O/A/P | Por nota |
| **NOM-004 compliance** | 100% | Notas que siguen formato NOM-004 | Por nota |
| **Doctor modifications** | <20% | Notas que médico modifica significativamente | Mensual |

**Cómo se mide**:
- Validador automático de schema SOAP
- Review de médicos: ¿Cuántas notas editaste?
- Logs de modificaciones post-generación

---

## 4. Data Integrity

### 4.1 Audit Trail

| Métrica | Target | Cálculo | Frecuencia |
|---------|--------|---------|------------|
| **Events with SHA256 hash** | 100% | (Eventos con hash / Total eventos) × 100 | Diario |
| **Export manifests** | 100% | (Exports con manifest / Total exports) × 100 | Por export |
| **Audit log completeness** | 100% | Todas las operaciones críticas registradas | Diario |

**Cómo se mide**:
- `backend/audit_logs.py` captura automáticamente
- Validador: `python3 backend/export_policy.py validate`
- Reporte diario: `/logs/audit-completeness.log`

### 4.2 Data Retention

| Métrica | Target | Cálculo | Frecuencia |
|---------|--------|---------|------------|
| **No data loss** | 100% | Eventos preservados sin mutación | Acumulado |
| **Backup frequency** | Diario | Git bundles generados automáticamente | Diario |
| **Corpus size growth** | Monitoreado | MB añadidos por día | Diario |

**Cómo se mide**:
- Append-only policy enforcement (no mutations)
- `scripts/sprint-close.sh` genera backups
- `du -sh storage/corpus.h5` para tamaño

### 4.3 Clips & Manifests

| Métrica | Target | Cálculo | Frecuencia |
|---------|--------|---------|------------|
| **Clip length** | <30 segundos | Duración promedio de audios/videos capturados | Por clip |
| **Hash+manifest coverage** | 100% | Clips con manifest SHA256 | Por clip |
| **MTTR for spikes** | <2 horas | Tiempo hasta resolver anomalías de telemetría | Por spike |

**Cómo se mide**:
- Metadata de clips en event store
- `backend/export_policy.py` valida manifests
- Alertas automáticas en Prometheus (futuro)

---

## 📊 Dashboard & Reporting

### Weekly Report

Enviado cada viernes a cliente:

```
Free Intelligence Cold — Weekly Report
Semana: [N] / 8 | Piloto: [Cliente]

🟢 Technical Performance:
- Uptime: 98.5% (target: >95%) ✅
- Avg response time: 2.1s (target: <3s) ✅
- Critical errors: 0 ✅

🟢 User Adoption:
- DAU: 85% (target: ≥80%) ✅
- Consultations: 42 (avg 6/día) ✅
- Satisfaction: 4.2/5 (target: ≥4/5) ✅

🟢 Clinical Impact:
- Time saved: 35% (target: ≥30%) ✅
- SOAP notes: 42 (target: ≥30 acum) ✅
- Triage accuracy: 93% (target: ≥90%) ✅

🟢 Data Integrity:
- SHA256 coverage: 100% ✅
- No data loss: ✅
- Backups: 7/7 días ✅

Next steps: [Acciones si aplica]
```

### Final Report (Day 60)

Incluye:
- Todas las métricas acumuladas
- Gráficas de tendencias
- Testimonios de usuarios
- Recomendación: Continuar / No continuar
- Plan de producción (si aplica)

---

## 🚨 Alertas Automáticas

### Critical Alerts (Acción inmediata)

| Alert | Threshold | Action |
|-------|-----------|--------|
| **System down** | >5 minutos | Notificar soporte FI + cliente IT |
| **Error rate spike** | >10 errores/hora | Review logs + hotfix si necesario |
| **Zero usage** | 0 consultas en 24h | Check con cliente si sistema en uso |

### Warning Alerts (Monitorear)

| Alert | Threshold | Action |
|-------|-----------|--------|
| **Slow response** | >5 segundos p95 | Investigar performance |
| **Low satisfaction** | <3.5/5 en encuesta | Call con usuario insatisfecho |
| **Backup failed** | Falta backup diario | Rerun script manualmente |

---

## 📈 Success Criteria Summary

Para que el piloto se considere **exitoso** y continúe a producción:

### Must-Have (Obligatorios)

- ✅ Uptime >95%
- ✅ Doctor satisfaction ≥4/5
- ✅ Time saved ≥30%
- ✅ Zero critical errors
- ✅ 100% SHA256 coverage
- ✅ Cliente confirma valor (cualitativo)

### Nice-to-Have (Deseables)

- ✅ SOAP notes ≥50 (vs target 30)
- ✅ Triage accuracy ≥95% (vs target 90%)
- ✅ NPS ≥70 (vs target 50)
- ✅ Referral to otros médicos/clínicas

---

## 🔗 Related Documents

- **One-pager**: `docs/sales/FI-COLD-ONE-PAGER.md`
- **LOI Template**: `docs/sales/LOI-TEMPLATE.md`
- **SOW Template**: `docs/sales/SOW-TEMPLATE.md`
- **Demo Script**: `docs/sales/DEMO-SCRIPT-VAR.md`
- **Baseline GTM**: `docs/sales/GTM-BASELINE.md`

---

**Status**: KPIs definidos ✅
**Next step**: Trackear métricas durante pilotos
**Owner**: Bernard Uriza Orozco
**Última actualización**: 2025-10-28
