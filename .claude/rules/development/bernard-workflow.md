# Cómo Trabajar con Bernard

Bernard valora: **simplicidad, enfoque, no tangentes, resultados rápidos.**

## Flujo Simple (seguir en orden)

1. Entender qué se pide (NO asumir más)
2. Hacer el cambio mínimo necesario
3. Verificar localmente (`curl`, `make dev-all`)
4. Commit → Push → PR
5. LISTO. No agregar más.

## ❌ Prohibido

- Ir por tangentes ("y también podríamos...")
- Ofrecer soluciones no pedidas
- Complicar lo simple
- Hacer deploy manual cuando existe CI/CD
- Preguntar sobre cosas no relacionadas
- Perder el enfoque del task original

## ✅ Correcto

- Enfocarse SOLO en lo que se pidió
- Verificar local → commit → PR → LISTO
- Si hay duda, PREGUNTAR antes de actuar
- Mantener respuestas cortas cuando Bernard está irritado

## Ejemplo de Error (NO HACER)

```
Bernard: "Revisa que /downloads existe"
Claude: *intenta deploy con rsync, pregunta sobre DMG, va por tangentes*
```

## Ejemplo Correcto

```
Bernard: "Revisa que /downloads existe"
Claude: curl localhost:9000/downloads/ → "Existe ✅" → fin
```

## Git Workflow Específico

```bash
# FLUJO OBLIGATORIO:
1. Trabajar SIEMPRE en rama `dev`
2. Commit cambios a `dev`
3. Push a `dev`
4. Crear PR de `dev` → `main`
5. Esperar aprobación del AI Gatekeeper (GPT-5)
6. Merge PR (nunca push directo)
```

**Razón:** main es producción, dev es desarrollo. El AI Gatekeeper revisa TODOS los cambios. Push directo a main deja dev desincronizada.

## Claude Debe Verificar Antes de Cada Push

1. ¿Estoy en la rama correcta? (debe ser dev)
2. ¿Voy a crear un PR? (debe ser sí)
3. ¿Voy a esperar review? (debe ser sí)

**Ver también:** `.claude/rules/development/git-workflow.md` para detalles completos del workflow
