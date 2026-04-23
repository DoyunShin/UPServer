FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY backend/pyproject.toml ./
COPY backend/uv.lock* ./
COPY backend/oryups ./oryups
RUN uv sync --no-dev

ENV PATH="/app/.venv/bin:${PATH}"
EXPOSE 80

CMD ["ups", "--config", "/app/config.json", "--host", "0.0.0.0", "--port", "80"]
