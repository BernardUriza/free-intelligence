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

# Copy app code. personas/insult/ contains the bot; shared/ is imported at runtime.
COPY personas/ personas/
COPY shared/ shared/
COPY persona.md .

# Create storage dir (legacy SQLite path — Postgres is authoritative
# now but the dir is still referenced by some import-time code).
RUN mkdir -p storage

CMD ["python", "-m", "personas.insult", "run"]
