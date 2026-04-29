FROM harbor.ai.adports.ae/orbit/python-base:3.12-slim

WORKDIR /app
COPY pyproject.toml poetry.lock* ./
RUN pip install --no-cache-dir poetry==1.8.3 \
    && poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction

COPY app/ ./app/
COPY policies/ ./policies/

ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
