# Chaos Drill Plan - Q4 2025

**Card**: FI-RELIABILITY-STR-001
**Related**: ERROR_BUDGETS.md
**Owner**: SRE Team
**Created**: 2025-10-29

---

## Primer Drill Agendado

### **Drill #1: Network Partition Simulation**

**Fecha**: 2025-11-15 14:00-15:30 CST
**Duración**: 90 minutos
**Owner**: @sre-lead
**Participants**: Backend team, On-call engineer

---

## Objetivos

1. ✅ Verificar que queue buffer puede retener 1h de writes durante network partition
2. ✅ Validar auto-reconnect logic cuando network se restaura
3. ✅ Confirmar que no hay pérdida de datos (all queued items procesados)
4. ✅ Medir recovery time (target: <2 minutos)

---

## Pre-Drill Checklist

**1 semana antes** (2025-11-08):
- [ ] Announce en #sre: "🔥 Chaos drill Nov 15: Network partition"
- [ ] Review `docs/runbooks/NETWORK_PARTITION.md`
- [ ] Preparar rollback plan (ver abajo)
- [ ] Configurar monitoring dashboards:
  - Queue depth (real-time)
  - Network latency (ping corpus host)
  - Write success rate
  - Recovery time metric

**1 día antes** (2025-11-14):
- [ ] Verificar que no hay deployments críticos el día del drill
- [ ] Backup de corpus.h5 (snapshot pre-drill)
- [ ] Test de rollback plan (dry run)
- [ ] Confirmar asistencia de participants

**1 hora antes** (13:00):
- [ ] Open Zoom call
- [ ] Abrir dashboards en pantalla compartida
- [ ] Verificar que production traffic es <50% de capacidad (safety margin)

---

## Drill Execution Plan

### Phase 1: Inject Chaos (14:00-14:15)

**Acción**: Simular network partition usando `iptables`

```bash
# En servidor de corpus.h5
sudo iptables -A INPUT -s <ingestion_api_ip> -j DROP
sudo iptables -A OUTPUT -d <ingestion_api_ip> -j DROP
```

**Expected Behavior**:
- Ingestion API detecta timeout al escribir a HDF5
- Queue local empieza a acumular writes
- Logs: `CORPUS_UNREACHABLE` cada 30s
- Dashboard: Queue depth aumentando linealmente

**Success Criteria**:
- Queue depth <10,000 items (safety limit)
- No crashes en Ingestion API
- Logs muestran retry attempts

---

### Phase 2: Observe Degradation (14:15-14:45)

**Monitoring**:
- Queue depth (debería crecer ~50 items/min)
- Memory usage de Ingestion API (no debe exceder 2GB)
- Alertas de Slack (`CORPUS_UNREACHABLE`)

**Validations**:
- ✅ Requests nuevos siguen siendo aceptados (HTTP 202)
- ✅ No hay memory leak en queue buffer
- ✅ Logs confirman `RETRY_SCHEDULED` cada 30s

**Actions**:
- Tomar screenshots de dashboards cada 10 min
- Documentar observaciones en shared doc

---

### Phase 3: Restore Network (14:45-15:00)

**Acción**: Remover iptables rules

```bash
# En servidor de corpus.h5
sudo iptables -D INPUT -s <ingestion_api_ip> -j DROP
sudo iptables -D OUTPUT -d <ingestion_api_ip> -j DROP
```

**Expected Behavior**:
- Ingestion API detecta network restored
- Queue empieza a drenar items acumulados
- Dashboard: Queue depth decrece

**Success Criteria**:
- Queue depth llega a 0 en <2 minutos
- No pérdida de datos (verify hash chain)
- Logs: `QUEUE_DRAINED` al final

---

### Phase 4: Validation & Cleanup (15:00-15:30)

**Validations**:
1. **Data integrity**: Verify que todos los items en queue fueron escritos
   ```bash
   python scripts/verify_corpus_integrity.py --since "2025-11-15 14:00"
   ```

2. **Performance**: p95 latency volvió a <2s

3. **No duplicates**: Hash check para detectar writes duplicados

**Cleanup**:
- Restore iptables rules originales (si aplicable)
- Close monitoring windows
- Archive screenshots en `docs/drills/2025-11-15/`

---

## Rollback Plan

**Si queue depth >10,000**:
1. Activar circuit breaker (stop accepting new requests)
2. Restore network inmediatamente
3. Drain queue prioritizando items críticos
4. Re-enable ingestion cuando queue <1,000

**Si memory >3GB**:
1. Restart Ingestion API service
2. Queue items se pierden (acceptable para drill)
3. Log incident para mejorar queue persistence

**Si drill debe cancelarse**:
1. Restore network
2. Monitor recovery por 30 min
3. Write post-mortem explicando cancelación

---

## Success Criteria (Overall)

| Criterio | Target | Medición |
|----------|--------|----------|
| **Queue resilience** | Retiene 1h de writes | Queue depth <10k |
| **Auto-recovery** | Reconnect <2min | Logs timestamp |
| **Data integrity** | 0 pérdidas | Hash verification |
| **No crashes** | API uptime 100% | Process monitoring |

---

## Post-Drill Deliverables

**Dentro de 2 días** (2025-11-17):
1. [ ] Post-mortem en `docs/drills/2025-11-15/POST_MORTEM.md`
2. [ ] Update `ERROR_BUDGETS.md` si descubrimos nuevos SLOs necesarios
3. [ ] File issues en GitHub para mejoras:
   - Persistir queue a disk (si vimos risk de pérdida)
   - Mejorar reconnect logic (si recovery >2min)
   - Dashboard de queue health (si faltó visibilidad)
4. [ ] Schedule Drill #2 (target: Dec 20)

---

## Próximos Drills (Calendario)

| Mes | Fecha | Drill Type | Objetivo |
|-----|-------|-----------|----------|
| **Nov 2025** | 2025-11-15 ✅ | Network partition | Queue resilience |
| Dec 2025 | 2025-12-20 | Corpus file lock | Concurrent access |
| Jan 2026 | 2026-01-17 | LLM timeout storm | Circuit breaker |
| Feb 2026 | 2026-02-14 | Disk 90% full | Log cleanup |

---

## Template para Próximos Drills

Usar este doc como template. Para cada nuevo drill:

1. Copy este archivo → `CHAOS_DRILL_<TYPE>_<DATE>.md`
2. Update objetivos y success criteria
3. Definir injection method específica
4. Preparar rollback plan para ese scenario
5. File en GitHub Project con label `chaos-drill`

---

_"El caos no se evita. Se practica."_
