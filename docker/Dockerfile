FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY alembic.ini ./
COPY alembic ./alembic

RUN pip install --no-cache-dir .

RUN useradd --create-home --uid 1000 msgate \
    && mkdir -p /app/data /app/data/logs \
    && chown -R msgate:msgate /app

USER msgate

EXPOSE 1025 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8080/healthz || exit 1

CMD ["msgate", "serve", "--api-host", "0.0.0.0"]
