# Imagen de COOPGESTION para desarrollo y producción.
# El proyecto se instala con uv; el entorno virtual vive en /app/.venv.

FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# libpq5: cliente de PostgreSQL. postgresql-client: aporta pg_isready para la espera.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 postgresql-client curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

# Primero las dependencias: así la caché de capas se reutiliza si no cambian.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN chmod +x docker/entrypoint.sh \
    && mkdir -p logs media staticfiles

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/cuentas/login/ > /dev/null || exit 1

ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "60", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
