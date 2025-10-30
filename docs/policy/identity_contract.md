# Identity Contract (Agent Determinism)

## Principio

La "identidad" del agente = plantilla versionada (determinística) + snapshot de políticas.

Misma pregunta + mismo estado → misma respuesta + provenance completo.

## Componentes

1. **agent_id**: UUID único del agente (e.g., `agent_claude_3_sonnet_v1`)
2. **prompt_template_v**: Versión de plantilla (e.g., `intake_coach_v2.json`)
3. **policy_snapshot_id**: Hash del snapshot de políticas activas
4. **source_ids[]**: Lista de IDs de artefactos fuente consultados
5. **answer_hash**: SHA256 de la respuesta generada

## Garantías

- **Reproducibilidad**: Puedes reconstruir sesión bit-a-bit con provenance.
- **Auditoría**: Toda interacción registrada con huellas criptográficas.
- **Versionamiento**: Cambios en plantillas/políticas → nueva versión → nuevo identity contract.

## Implementación

Ver: `config/agent.yaml` (plantillas y versiones)

Endpoint: `POST /api/sessions/{id}/events` guarda metadata:
```json
{
  "agent_id": "agent_claude_3_sonnet_v1",
  "prompt_template_v": "intake_coach_v2",
  "policy_snapshot_id": "sha256:abc123...",
  "source_ids": ["doc_001", "doc_002"],
  "answer_hash": "sha256:def456..."
}
```

## Validación

```bash
# Verificar identity contract de una sesión
curl http://localhost:7001/api/sessions/{id}/provenance
```

Debe retornar todos los elementos del contrato de identidad con hashes verificables.
