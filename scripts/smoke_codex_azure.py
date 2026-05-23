#!/usr/bin/env python3
"""Smoke-test: ALICE's codex+Azure path, end to end, against the REAL Azure key.

Replicates `alice/core/llm.py`'s wiring (fi_runner.CodexBackend over the shared
Azure OpenAI deployment) and runs ONE live `codex exec --json` turn, then prints
the parsed text + token usage + thread/session id + latency, and validates the
LLMResponse contract. Run this BEFORE pushing the alice swap so the first real
codex turn does NOT happen in prod ("verify before celebrate").

It does NOT import `alice.core.llm` (that lives on `main`, not necessarily the
checked-out branch) — it rebuilds the exact same backend wiring, so it works on
any branch. It DOES read the same Azure config alice reads: `alice.config`
settings first, then `AZURE_OPENAI_{ENDPOINT,KEY,GPT_DEPLOYMENT}` env vars.

Usage (from ~/Documents/discord-bot, in the conda env / .venv that has fi-runner):
    python scripts/smoke_codex_azure.py
    python scripts/smoke_codex_azure.py "tu mensaje de prueba"

Exit code 0 = OK (text + usage came back). Non-zero = a gate failed.
The Azure key is NEVER printed (only "***set***").
"""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
import time


def _load_azure_config() -> tuple[str, str, str, str]:
    """Return (endpoint, api_key, deployment, source) the way alice resolves it."""
    try:
        from alice.config import settings  # type: ignore[import-not-found]

        return (
            settings.azure_openai_endpoint,
            settings.azure_openai_key,
            settings.azure_openai_gpt_deployment,
            "alice.config.settings",
        )
    except Exception as exc:  # broad on purpose: the env-var fallback is intentional
        print(f"  (alice.config no disponible: {exc!r} -> uso env vars)")
        return (
            os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
            os.environ.get("AZURE_OPENAI_API_KEY") or os.environ.get("AZURE_OPENAI_KEY", ""),
            os.environ.get("AZURE_OPENAI_GPT_DEPLOYMENT", ""),
            "env vars",
        )


async def main() -> int:
    user_msg = sys.argv[1] if len(sys.argv) > 1 else "Hola, ¿cómo estás? Responde en una sola frase."
    print("== Smoke test: codex + Azure OpenAI (path de ALICE) ==\n")

    # 1) codex CLI presente?
    codex = shutil.which("codex")
    if not codex:
        print("FALLA: el `codex` CLI no esta en PATH. Instalalo: npm i -g @openai/codex")
        return 1
    print(f"[ok] codex CLI: {codex}")

    # 2) fi_runner importable?
    try:
        from fi_runner import CodexBackend, PermissionMode, Runner, ToolPolicy
    except ImportError as exc:
        print(f"FALLA: no se pudo importar fi_runner ({exc}). Usa el venv con fi-runner instalado.")
        return 1
    print("[ok] fi_runner importable")

    # 3) Azure config (igual que alice)
    endpoint, api_key, deployment, src = _load_azure_config()
    print(f"[ok] Azure config desde: {src}")
    print(f"     endpoint:   {endpoint or '(VACIO!)'}")
    print(f"     deployment: {deployment or '(VACIO!)'}")
    print(f"     api_key:    {'***set***' if api_key else '(VACIO!)'}")  # nunca imprimir la key
    if not (endpoint and api_key and deployment):
        print("FALLA: falta endpoint/api_key/deployment. Revisa .env o las env vars AZURE_OPENAI_*.")
        return 1

    # 4) Bridge de la key al env var que codex lee (identico a alice.__init__)
    key_env = "AZURE_OPENAI_API_KEY"
    os.environ.setdefault(key_env, api_key)

    # 5) Backend EXACTO de alice + un turno real
    backend = CodexBackend(default_model=deployment, azure_endpoint=endpoint, azure_api_key_env=key_env)
    runner = Runner(
        backend=backend,
        persona="Eres ALICE, una presencia empatica y breve.",
        tool_policy=ToolPolicy(permission_mode=PermissionMode.DEFAULT),
        model=deployment,
    )
    print(f"\n-> Turno real: {user_msg!r}")
    print("   (invoca `codex exec --json` contra tu Azure; puede tardar unos segundos)\n")

    start = time.monotonic()
    try:
        result = await runner.run(f"user: {user_msg}")
    except Exception as exc:  # broad on purpose: queremos ver el error crudo de codex
        print(f"FALLA en el turno: {type(exc).__name__}: {exc}")
        print("\nPistas: 401/403 -> key o endpoint mal; 404 -> deployment inexistente;")
        print("'wire_api'/Responses -> el deployment debe ser gpt-4o/gpt-4.1 (no legacy gpt-4).")
        return 1
    latency_ms = int((time.monotonic() - start) * 1000)

    # 6) Resultado + validacion del contrato LLMResponse
    usage = result.usage or {}
    print("== RESULTADO ==")
    print(f"  text:       {result.text!r}")
    print(f"  usage:      {usage}")
    print(f"  session_id: {result.session_id}")
    print(f"  latency:    {latency_ms} ms\n")

    ok = True
    if not result.text.strip():
        print("  [warn] text vacio -- el modelo no respondio (revisa deployment/wire_api)")
        ok = False
    if not (usage.get("input_tokens") or usage.get("output_tokens")):
        print("  [warn] sin usage -- codex no reporto tokens (no llego turn.completed?)")
        ok = False

    if ok:
        print("OK -- alice puede correr sobre codex+Azure. Listo para pushear el deploy.")
        return 0
    print("Hubo warnings -- NO deployar hasta resolverlos.")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
