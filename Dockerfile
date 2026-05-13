# Microsoft Container Registry mirror — Docker Hub's anonymous pull limit
# (100 pulls / 6h / IP) was breaking ACR builds that triggered close together
# (e.g. when CD ran for 3 commits in a single hour). MCR has no equivalent
# anonymous rate limit and provides Python 3.14 official builds for both
# amd64 and arm64. Bumped from python:3.14-slim → mcr.microsoft.com on
# 2026-05-05 after CD failed mid-deploy on v3.7.52.
FROM mcr.microsoft.com/devcontainers/python:3.14-bookworm

WORKDIR /app

# Install Python deps (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code. shared/ is imported by insult/__main__.py and
# insult/core/llm/retry.py since v3.9.8 — must be present at runtime.
COPY insult/ insult/
COPY shared/ shared/
COPY persona.md .

# Create storage dir for SQLite
RUN mkdir -p storage

CMD ["python", "-m", "insult", "run"]
