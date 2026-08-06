# persona-runner base — the shared conda env PLUS the runner's heavy toolchain.
#
# The runner needs what no other surface does: Node 22, the Claude Code CLI (the
# Agent SDK loop) and Playwright's headless Chromium for JS-heavy scraping. That
# toolchain is ~136s of the runner's build and changes about as often as the
# conda env — yet it was reinstalled on every commit, because `az acr build`
# carries no layer cache between runs.
#
# Split out and tagged by the SHA-256 of its inputs (`environment.yml` + this
# file), so it rebuilds only when the toolchain itself moves. The runner image
# on top is then pure COPY, and its push only ships the code layers instead of
# re-uploading a multi-GB Chromium.

ARG BASE_IMAGE=serverbotacr.azurecr.io/khimeras-base:latest
FROM ${BASE_IMAGE}

SHELL ["/bin/bash", "-l", "-c"]
WORKDIR /app

# Node-from-conda avoids the NodeSource apt repo + the OS-version-specific
# Bookworm-has-18 dance — everything stays inside one package manager.
RUN mamba install -n base -c conda-forge -y 'nodejs>=22,<23' \
 && mamba clean --all --yes \
 && find /opt/conda/ -follow -type f -name '*.a' -delete \
 && find /opt/conda/ -follow -type f -name '*.pyc' -delete

# OAuth Max credentials get mounted at runtime via
# /home/runner/.claude/.credentials.json (NOT baked into the image).
RUN npm install -g --silent @anthropic-ai/claude-code

# Playwright MCP server + headless Chromium for scraping JS-heavy / social-media
# sites (IG/FB/TikTok/X) that web_search cannot reach. Chromium lives at
# PLAYWRIGHT_BROWSERS_PATH so the non-root runner user can read it. apt deps
# (libnss3, libgbm, libxcomposite, libxdamage, libasound, etc.) are pulled in
# by `--with-deps`, which needs root — done here, before any USER switch.
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers
RUN npm install -g --silent @playwright/mcp \
 && npx -y playwright install --with-deps chromium \
 && chmod -R a+rX /opt/playwright-browsers
