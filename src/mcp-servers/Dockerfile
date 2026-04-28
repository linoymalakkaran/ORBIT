# Generic MCP server Dockerfile — build with: --build-arg SERVER=keycloak-mcp
ARG SERVER=keycloak-mcp

FROM harbor.ai.adports.ae/python:3.12-slim AS builder
WORKDIR /app
RUN pip install poetry==1.8.3 && poetry config virtualenvs.in-project true
COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-dev --no-interaction --no-ansi

FROM harbor.ai.adports.ae/python:3.12-slim AS runtime
ARG SERVER
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY shared/ ./shared/
COPY ${SERVER}/ ./${SERVER}/
COPY registry/ ./registry/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

RUN groupadd -g 1000 appgroup && useradd -u 1000 -g appgroup -s /bin/sh appuser
USER 1000
EXPOSE 8000
CMD uvicorn ${SERVER}.main:app --host 0.0.0.0 --port 8000
