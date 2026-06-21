# Conda-native base — required by the data-pipeline architecture
# (memory: feedback_no_pypi_only_conda). Using Quay.io instead of
# Docker Hub for the same anonymous-pull-limit reason that drove the
# original MCR switch (memory: reference_dockerfile_base_mcr) — Quay
# does not impose the same rate cap.
FROM quay.io/condaforge/miniforge3:26.1.1-3

# Mamba is pre-installed on miniforge. It resolves environments ~5x
# faster than classic conda — matters during cold CD builds.
SHELL ["/bin/bash", "-l", "-c"]
WORKDIR /app

# Install conda env into `base` so the default PATH already includes
# the right Python. Avoids needing `conda activate` in CMD which is
# unfriendly in container PID-1 contexts. Clean caches at the end to
# shave ~80MB off the image.
COPY environment.yml .
RUN mamba env update -n base -f environment.yml \
 && mamba clean --all --yes \
 && find /opt/conda/ -follow -type f -name '*.a' -delete \
 && find /opt/conda/ -follow -type f -name '*.pyc' -delete

# The demux HOST's gpt-4.1 brain (demux_ai.host_llm.HostRouterLLM) runs through
# fi_runner.CodexBackend, which shells out to the `codex` npm CLI pointed at the
# shared Azure OpenAI endpoint (no ChatGPT login — just the Azure key bridged into
# AZURE_OPENAI_API_KEY at runtime). Both host gpt-4.1 paths in THIS plumbing image
# need it: the host_degrader (host_router_enabled) and the LLM shadow router
# (llm_shadow_router_enabled, HOST 5/6 slice A.2). Without the CLI the gpt-4.1 call
# fails with BackendError("requires the codex CLI on PATH") — wrapped/invisible for
# the shadow, but the capability never actually works. Mirrors Dockerfile.alice.
RUN mamba install -n base -y nodejs \
 && npm i -g @openai/codex \
 && mamba clean --all --yes \
 && find /opt/conda/ -follow -type f -name '*.pyc' -delete

# Copy app code. personas/insult/ contains the bot; shared/ + khimeras_shared/
# are imported at runtime. khimeras_shared/ is MANDATORY: the demux (PR #26,
# Etapa 3) moved neutral capabilities there and personas.insult.app imports
# `from khimeras_shared.runner.agent_client import AgentRunnerClient` at boot —
# omitting it makes the plumbing crashloop on start with
# `ModuleNotFoundError: No module named 'khimeras_shared'` (prod near-miss
# 2026-06-16: a pre-demux revision kept serving so /health stayed green while
# every new discord-bot revision failed to boot).
COPY personas/ personas/
COPY shared/ shared/
COPY khimeras_shared/ khimeras_shared/
# demux_ai/ — PR-4b slice 3: the persona composition root can import
# `demux_ai.host_degrader` when `host_router_enabled` is True. Gated off in prod,
# but the file must ship so flipping the flag never 502s with ModuleNotFoundError.
# Enforced by tests/arch/test_runner_dockerfile_copies_imports.py.
COPY demux_ai/ demux_ai/
COPY persona.md .

# Create storage dir (legacy SQLite path — Postgres is authoritative
# now but the dir is still referenced by some import-time code).
RUN mkdir -p storage

CMD ["python", "-m", "personas.insult", "run"]
