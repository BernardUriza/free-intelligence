# Letter of Intent (LOI) — Free Intelligence Cold Pilot

**Plantilla para pilotos de 60 días**
**Version**: 1.0
**Fecha**: Octubre 2025

---

## CARTA DE INTENCIÓN

### Entre

**PROVEEDOR**:
Free Intelligence
Bernard Uriza Orozco
[Dirección por definir]
RFC: [Por definir]
Representante Legal: Bernard Uriza Orozco

**CLIENTE**:
[Nombre de la clínica/hospital]
[Dirección completa]
RFC: [RFC del cliente]
Representante Legal: [Nombre y cargo]

**Fecha de emisión**: [DD/MM/AAAA]

---

## 1. OBJETO

Las partes expresan su intención de iniciar un **piloto de 60 días** del sistema **Free Intelligence Cold** para consultas médicas asistidas por IA, con el objetivo de evaluar su viabilidad técnica y comercial para implementación en producción.

### Alcance del Piloto

El sistema **FI-Cold** incluye:

1. **IntakeCoach**: Asistente de intake médico (triage + recopilación de datos)
2. **Generador SOAP**: Notas médicas NOM-004-SSA3-2012 compliant
3. **Backend FI**: Event store local (HDF5) con audit trail completo
4. **AURITY Frontend**: Interfaz web para médicos y staff administrativo
5. **Ollama LLM**: Modelo de lenguaje local (sin envío de datos a cloud)

**Modalidad**: Sin PHI persistente durante piloto (datos demo/anonimizados)

---

## 2. TÉRMINOS DEL PILOTO

### 2.1 Duración

- **Inicio**: [DD/MM/AAAA]
- **Fin**: [DD/MM/AAAA + 60 días]
- **Extensión**: Posible hasta 30 días adicionales con acuerdo mutuo

### 2.2 Ubicación

- **Instalación**: [Especificar consultorios/área de prueba]
- **Usuarios piloto**: [Número de médicos + staff administrativo]
- **Hardware**: Proporcionado por [Free Intelligence / Cliente]

### 2.3 Inversión Durante Piloto

| Concepto | Responsable | Costo |
|----------|-------------|-------|
| **Hardware demo** (laptop/servidor) | Free Intelligence | Sin costo |
| **Software FI-Cold** (licencia temporal) | Free Intelligence | Sin costo |
| **Implementación on-site** (1 día) | Free Intelligence | Sin costo |
| **Capacitación** (médicos + staff, 4h) | Free Intelligence | Sin costo |
| **Soporte técnico remoto** (60 días) | Free Intelligence | Sin costo |
| **Internet/infraestructura existente** | Cliente | Cliente asume |

**Total inversión cliente durante piloto**: **$0 MXN**

---

## 3. CRITERIOS DE ÉXITO

### 3.1 Métricas Técnicas

| Métrica | Target Mínimo | Medición |
|---------|---------------|----------|
| **Uptime** | >95% | Monitoreo automático |
| **Tiempo de respuesta** | <3 segundos | Promedio por consulta |
| **Notas SOAP generadas** | ≥30 notas | Durante 60 días |
| **Errores críticos** | 0 | Logs de sistema |

### 3.2 Métricas de Usuario

| Métrica | Target Mínimo | Medición |
|---------|---------------|----------|
| **Satisfacción médicos** | ≥4/5 | Encuesta fin de piloto |
| **Tiempo ahorrado** | ≥30% | Comparativa pre/post |
| **Adopción staff** | ≥80% | Logs de uso |
| **Errores reportados** | <5 críticos | Registro incidencias |

### 3.3 Criterios de Conversión a Producción

El piloto se considera **exitoso** si:
- ✅ Métricas técnicas cumplen targets mínimos
- ✅ Satisfacción médicos ≥4/5
- ✅ Cliente confirma ahorro de tiempo real (≥20%)
- ✅ No hay objeciones legales/IT insalvables

---

## 4. COMPROMISOS DE LAS PARTES

### 4.1 Compromisos de Free Intelligence

1. **Instalación**: Configurar sistema en sitio en 1 día hábil
2. **Capacitación**: 4 horas presenciales (médicos + staff administrativo)
3. **Soporte**: Respuesta <24h a incidencias vía email/WhatsApp
4. **Monitoreo**: Logs de uso y reportes semanales
5. **Fixes**: Bugs críticos corregidos en <48h
6. **Documentación**: Guías de usuario + videos tutoriales

### 4.2 Compromisos del Cliente

1. **Acceso**: Proporcionar acceso a instalaciones y red LAN
2. **Usuarios**: Asignar 2-4 médicos para usar sistema durante piloto
3. **Feedback**: Encuestas de satisfacción (semanal + final)
4. **Datos demo**: Proveer casos anónimos para testing (opcional)
5. **Decisión**: Notificar intención de continuar o no al día 50 del piloto

---

## 5. DATOS Y CONFIDENCIALIDAD

### 5.1 Datos Durante Piloto

Durante el piloto **FI-Cold**:
- ❌ **NO se capturará PHI real** (nombres, fechas de nacimiento, direcciones)
- ✅ **Se usarán casos demo** o datos completamente anonimizados
- ✅ **Todos los datos permanecen en LAN** del cliente (no hay egreso a internet)

### 5.2 Confidencialidad

Ambas partes se comprometen a:
- No divulgar información confidencial de la otra parte
- No usar información del piloto para fines distintos a la evaluación
- Destruir o devolver información confidencial al término del piloto

### 5.3 Propiedad Intelectual

- **Software FI**: Propiedad de Free Intelligence
- **Datos generados**: Propiedad del Cliente
- **Mejoras/feedback**: Compartido para beneficio mutuo

---

## 6. CONVERSIÓN A PRODUCCIÓN

### 6.1 Opciones Post-Piloto

Al término de los 60 días, el Cliente puede:

**Opción A: Continuar (Producción)**
- Firmar contrato comercial con términos definitivos
- Migrar a hardware de producción (si aplica)
- Habilitar captura de PHI con compliance NOM-024
- Pricing: Ver one-pager FI-Cold (compra o leasing)

**Opción B: No Continuar**
- Free Intelligence retira hardware demo (si aplica)
- Cliente retiene datos generados durante piloto
- Sin penalizaciones para ninguna parte

### 6.2 Timeline de Conversión

Si Cliente decide continuar:
- **Día 50**: Cliente notifica intención
- **Día 60**: Fin de piloto + reporte final
- **Día 75**: Firma de contrato comercial
- **Día 90**: Sistema en producción con PHI

---

## 7. TERMINACIÓN ANTICIPADA

Cualquiera de las partes puede terminar el piloto anticipadamente con:
- **Notificación**: 7 días de anticipación por escrito
- **Causa justificada**: Incumplimiento material de compromisos
- **Sin penalización**: Ambas partes liberadas de obligaciones futuras

Causas de terminación justificada:
- **Free Intelligence**: Cliente no proporciona acceso o usuarios
- **Cliente**: Sistema no funciona según especificaciones técnicas

---

## 8. LIMITACIÓN DE RESPONSABILIDAD

### 8.1 Durante Piloto

Free Intelligence **NO se hace responsable** de:
- Pérdida de datos (piloto es para evaluación, no producción)
- Decisiones médicas tomadas con asistencia del sistema
- Daños indirectos o lucro cesante

**Responsabilidad máxima**: Limitada al costo del hardware demo (si aplica)

### 8.2 Uso del Sistema

El Cliente reconoce que:
- FI-Cold es un **asistente**, no un dispositivo médico
- **El médico es responsable** de validar toda información generada
- El sistema **NO diagnostica ni prescribe** tratamientos

---

## 9. LEY APLICABLE Y JURISDICCIÓN

Este LOI se rige por las leyes de los Estados Unidos Mexicanos.

Cualquier controversia se resolverá en los tribunales de [Ciudad del Cliente], México.

---

## 10. FIRMAS

### Free Intelligence

**Nombre**: Bernard Uriza Orozco
**Cargo**: Fundador y Representante Legal
**Firma**: ________________________
**Fecha**: ________________________

### [Nombre del Cliente]

**Nombre**: [Nombre del representante legal]
**Cargo**: [Cargo del firmante]
**Firma**: ________________________
**Fecha**: ________________________

---

## ANEXO A: Especificaciones Técnicas

### Hardware Mínimo Requerido

**Opción 1: Hardware proporcionado por Free Intelligence**
- Laptop Dell Latitude 7430 (i7, 32GB RAM, 1TB SSD)
- Conexión ethernet a LAN del cliente

**Opción 2: Hardware del cliente** (si prefiere usar servidor existente)
- Server con Docker instalado
- 8GB RAM mínimo, 50GB disk disponible
- Conexión LAN 1Gbps
- Acceso root/admin

### Conectividad

- **Red LAN**: Requerida (no funciona sin red)
- **Internet**: Opcional (sistema funciona offline)
- **Puertos**: 7001 (backend), 9000 (frontend), 11434 (Ollama)

### Usuarios Concurrentes

- Piloto: 2-4 médicos + 2-3 staff administrativo
- Producción: Hasta 50 usuarios simultáneos (según hardware)

---

## ANEXO B: Cronograma Tentativo

| Semana | Actividades | Responsable |
|--------|-------------|-------------|
| **Día 1** | Instalación on-site + capacitación | FI |
| **Día 2-7** | Uso inicial + ajustes | Cliente + FI soporte |
| **Día 8-14** | Primera encuesta de satisfacción | FI |
| **Día 15-45** | Uso continuo + monitoreo | Cliente + FI soporte |
| **Día 46-50** | Decisión continuar/no continuar | Cliente |
| **Día 51-60** | Reporte final + plan de producción | FI |

---

## ANEXO C: Contactos

### Free Intelligence

**Soporte técnico**:
- Email: support@free-intelligence.health
- WhatsApp: [Por definir]
- Horario: Lun-Vie 9am-6pm (zona horaria Mexico City)

**Ventas/Comercial**:
- Email: bernard.uriza@free-intelligence.health
- WhatsApp: [Por definir]

### [Nombre del Cliente]

**Contacto principal**:
- Nombre: [Por definir]
- Email: [Por definir]
- Teléfono: [Por definir]

**Contacto técnico/IT**:
- Nombre: [Por definir]
- Email: [Por definir]
- Teléfono: [Por definir]

---

**NOTAS FINALES**:

1. Este LOI **no es un contrato vinculante** para producción
2. Es una expresión de intención para evaluar el sistema
3. Términos comerciales definitivos se negociarán post-piloto
4. Ambas partes operan de buena fe durante el piloto

---

**Versión**: 1.0
**Fecha de plantilla**: Octubre 2025
**Válido para**: Pilotos FI-Cold (sin PHI persistente)
