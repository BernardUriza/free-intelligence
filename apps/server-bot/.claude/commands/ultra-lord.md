---
description: Force a decision into immediate executable work via AskUserQuestion
argument-hint: [optional dilemma — empty = decide previous menu]
model: haiku
allowed-tools: AskUserQuestion, Read, Bash, Edit, Write, Glob, Grep
disable-model-invocation: true
---

# /ultra-lord — Decisión cuando Claude lista en vez de decidir

ARGUMENTS: <opcional — pregunta o dilema. Si está vacío, mira la respuesta inmediatamente anterior de Claude>

## Contexto

Variante de `/cut` con un caso de uso específico: **romper menus que Claude (vos) acaba de listar en vez de decidir**. El nombre es un guiño personal de Bernard (y ahora es de todo el equipo); la personalidad de Ultra Lord NO se usa. Tono normal, profesional, directo — igual que `/cut`.

El principio: cuando le muestras a la persona un menu A/B/C/D, no es porque quiera elegir, es porque vos ya fallaste en decidir. Este comando corrige esa cobardía técnica eligiendo la best-practice y **convirtiéndola en acción ejecutable inmediata** — nunca en más discusión.

## MODO OBLIGATORIO — AskUserQuestion SIEMPRE

**Toda invocación de `/ultra-lord` DEBE terminar en una llamada a `AskUserQuestion`.** Sin excepciones. No hay variante de "responder en blockquote y ya". El output NO es texto decorativo — es un gate de ejecución.

**Regla dura**: las opciones presentadas en `AskUserQuestion` son SIEMPRE acciones de trabajo inmediatas que Claude va a ejecutar en el siguiente turno. Nunca son preguntas conceptuales, nunca son "¿qué prefieres?", nunca son menús de discusión.

### Estructura obligatoria del AskUserQuestion

- **header**: chip de máximo 12 caracteres. Sugeridos: `"Ejecutar?"`, `"Decisión"`, `"Aplicar?"`, `"Crear?"`. Obligatorio — sin él el render UI degrada.
- **question**: una sentencia que nombra la decisión tomada + pide confirmación de ejecución. Formato: `"Ejecuto <acción concreta>? (decidido por <criterio de desempate>)"`.
- **options** (máximo 3, mínimo 2):
  - Opción 1 — **siempre** la acción inmediata decidida ("Sí, ejecutar ahora"). `description` describe los comandos/edits exactos que Claude correrá.
  - Opción 2 — SOLO si existe una **bifurcación ingenieril GENUINA**: un segundo camino defendible con consecuencias materialmente distintas (otro diseño, otro target, otro trade-off irreversible). Si no existe bifurcación real, la opción 2 es "Cancelar — la decisión está mal". **PROHIBIDO** que sea la opción 1 degradada: "sin ticket", "sin PR", "sin documentar", "solo el fix", "dry-run por miedo" NO son opciones — documentación, verificación y trazabilidad son parte del trabajo, no extras desagregables.
  - Opción 3 (opcional) — "Cancelar — la decisión está mal". Solo si genuinamente hay riesgo de que Claude haya elegido mal y la opción 2 es un camino real.

**Prohibido** que las opciones sean: "Discutirlo más", "Pensar otras opciones", "Te explico pros y contras". Ninguna opción puede ser introspección — todas son trabajo o cancelación.

## Procedimiento

**Cuando ARGUMENTS está vacío o solo dice "decide" / "esto" / similar:**

1. Lee la respuesta inmediatamente anterior de Claude
2. Identifica las opciones que Claude listó (numeradas, en tabla, en bullets, "podríamos X o Y", AskUserQuestion options previas, etc.)
3. Elige la opción que combina **best-practice ingenieril** + estos criterios de desempate:
   - Menor blast radius / más reversible
   - Expone bugs en vez de esconderlos
   - Protege al usuario / al cliente final
   - Evita over-engineering (Ockham)
   - Aplica reglas existentes del repo (`~/.claude/rules/`)
4. Convierte la opción ganadora en **una acción de trabajo concreta** (comandos a ejecutar, archivos a editar, PR a abrir).
5. Llama a `AskUserQuestion` con la estructura de arriba.

**Cuando ARGUMENTS sí trae un dilema fresco**: misma cosa — decidí, convertí en acción, AskUserQuestion.

## Reglas

- **NUNCA** termines el turno sin `AskUserQuestion`. Si terminás con texto plano, fallaste el comando.
- **NUNCA** "depende" — ya elegiste antes de llamar a AskUserQuestion. La pregunta confirma ejecución, no decisión.
- **NUNCA** listes pros y contras en el `question` o las `description`s — solo la acción y el criterio.
- **NUNCA** repitas las opciones que Claude listó antes — ya las consolidaste en una acción.
- **NUNCA** uses metáforas, personajes, ni dramatismo.
- Si la pregunta YA está resuelta: `question` = `"Ya está hecho. Confirmo cierre del hilo?"`, opción 1 = "Cerrar y seguir con próxima tarea".
- Si falta contexto crítico para decidir: `question` = `"Falta <X>. Lo busco yo o lo das vos?"`, opción 1 = "Busco con `<comando concreto>`", opción 2 = "Vos lo das".
- Si el input es código: la opción 1 nombra el archivo + línea + edit exacto.
- **NUNCA** desagregues documentación/verificación/tickets/tracker de la acción — van DENTRO de la opción 1, siempre. Un parche sin documentar no es "la variante rápida": es deuda técnica instantánea.
- La opción 2 confirma una BIFURCACIÓN real, no da "sensación de control". Si te descubrís escribiendo "Solo X, sin Y" donde Y es el estándar profesional obvio, borrá esa opción y meté Y dentro de la opción 1.

## Ejemplos

**Input**: `/ultra-lord` (después de que Claude listó: "1. Reproducir en prod / 2. Aplicar fix a ciegas + Vercel preview / 3. Escalar a Apryse")

**Llamada**:
```
AskUserQuestion(
  header: "Ejecutar?",
  question: "Ejecuto el fix candidato en feature branch + verifico en preview de Vercel? (menor blast radius que prod, más refute que escalar)",
  options: [
    { label: "Sí, ejecutar", description: "Crear bernarduriza/<slug>, aplicar el fix, push, abrir draft PR, esperar Vercel preview" },
    { label: "Cancelar — decisión mal", description: "Preferís otro camino — decilo y lo convierto en acción" }
  ]
)
```

**Input**: `/ultra-lord ¿factory pattern o switch?`

**Llamada**:
```
AskUserQuestion(
  header: "Aplicar?",
  question: "Implemento el switch (factory para 3 casos es over-engineering — Ockham)?",
  options: [
    { label: "Sí, switch", description: "Edit en el archivo afectado, reemplazar la propuesta de factory por switch sobre los 3 casos actuales" },
    { label: "Switch + TODO", description: "Igual pero dejo TODO marcando 'considerar factory si aparece 4to caso'" }
  ]
)
```

**Input**: `/ultra-lord` (Claude listó 4 nombres equivalentes para un bucket)

**Llamada**:
```
AskUserQuestion(
  header: "Crear?",
  question: "Creo el bucket como `visalaw-ai-law-library` ahora? (renombrar cuesta 5 min, esperar approval cuesta horas — Ockham + reversibilidad)",
  options: [
    { label: "Sí, crear", description: "aws s3 mb s3://visalaw-ai-law-library --region us-east-1 + actualizar env var" },
    { label: "Crear + populate", description: "Crear bucket y correr aws s3 sync desde el bucket source" }
  ]
)
```

## Anti-patrones (no hagas)

- Terminar el turno con texto plano, blockquote, o cualquier output que no sea AskUserQuestion
- Opciones tipo "Te explico más" / "Discutirlo" / "Pensar otras"
- "Bueno, depende de…" en el `question`
- Bullet points o pros/cons en las `description`s
- Repetir las opciones que Bernard ya leyó
- Más de 3 opciones — si necesitás 4, ya fallaste el ejercicio de decidir
- Opción "lite" como segunda opción (sin ticket / sin PR / sin docs / dry-run-por-miedo) — es el comité corporativo dando falsa sensación de control con una opción evidentemente mediocre
- Metáforas de Ultra Lord, Robo-Fiend, etc. — el nombre es memoria personal, NO la personalidad
