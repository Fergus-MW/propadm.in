FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.0 /uv /bin/uv
WORKDIR /app
COPY . /app
RUN uv sync --locked --no-dev --extra cloud
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app:/app/packages/core/src:/app/packages/runtime/src" \
    PYTHONUNBUFFERED=1 \
    PORT=8080
RUN useradd --uid 10001 --create-home propadmin && mkdir /data && chown propadmin /data
WORKDIR /app/services/ingestion
USER propadmin
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
