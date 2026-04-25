FROM node:20-alpine AS frontend

WORKDIR /frontend

# Install dependencies first so the layer caches when only source changes.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Build the SvelteKit static bundle. The svelte.config.js writes the
# output into ../backend/oryups/static, which the Python image picks up
# from the mounted source tree below.
COPY frontend/ ./
RUN rm -rf /backend-static && \
    mkdir -p /backend-static && \
    sed -i "s|'../backend/oryups/static'|'/backend-static'|g" svelte.config.js && \
    npm run build


FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY backend/pyproject.toml ./
COPY backend/uv.lock* ./
COPY backend/oryups ./oryups
RUN uv sync --no-dev

# Replace any in-tree static bundle with the freshly-built one so a stale
# checked-in copy can never ship in the image.
RUN rm -rf ./oryups/static
COPY --from=frontend /backend-static ./oryups/static

ENV PATH="/app/.venv/bin:${PATH}"
EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; \
        sys.exit(0 if urllib.request.urlopen('http://127.0.0.1/api/info', timeout=3).status==200 else 1)" \
    || exit 1

CMD ["ups", "--config", "/app/config.json", "--host", "0.0.0.0", "--port", "80"]
