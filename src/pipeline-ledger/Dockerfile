# ── Build stage ──────────────────────────────────────────────────────────────
FROM harbor.ai.adports.ae/python:3.12-slim AS builder
WORKDIR /app

RUN pip install poetry==1.8.3 && poetry config virtualenvs.in-project true
COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-dev --no-interaction --no-ansi

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM harbor.ai.adports.ae/python:3.12-slim AS runtime
WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY app/ ./app/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

RUN groupadd -g 1000 appgroup && useradd -u 1000 -g appgroup -s /bin/sh appuser
USER 1000

EXPOSE 8000
HEALTHCHECK CMD python -c "import httpx; httpx.get('http://localhost:8000/health/live').raise_for_status()"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
