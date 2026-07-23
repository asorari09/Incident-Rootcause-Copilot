# Build the small React operator dashboard.
FROM node:22-alpine AS web-build
WORKDIR /app/apps/web
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci
COPY apps/web ./
RUN npm run build

# Run one service: FastAPI, static dashboard, local data, and optional Chroma index.
FROM python:3.12-slim AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/apps/api/src \
    PATH=/app/.venv/bin:$PATH \
    IR_COPILOT_WEB_DIST=/app/web_dist \
    IR_COPILOT_ALLOW_MODEL_DOWNLOAD=true

RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev

COPY apps/api/src ./apps/api/src
COPY data/runbooks ./data/runbooks
COPY data/scenarios ./data/scenarios
COPY docker/entrypoint.sh ./docker/entrypoint.sh
COPY --from=web-build /app/apps/web/dist ./web_dist
RUN chmod +x ./docker/entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["uvicorn", "ir_copilot.main:app", "--host", "0.0.0.0", "--port", "8000"]
