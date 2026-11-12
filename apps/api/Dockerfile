FROM python:3.15-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /uvx /bin/

RUN useradd --create-home --uid 10001 app && mkdir -p /app && chown app:app /app

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_NO_DEV=1

COPY --chown=app:app pyproject.toml uv.lock* ./
COPY --chown=app:app apps/api apps/api
COPY --chown=app:app apps/worker apps/worker
COPY --chown=app:app apps/inference apps/inference
COPY --chown=app:app packages packages
COPY --chown=app:app ml ml
USER app
RUN uv sync --all-packages --no-dev

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "community_llm_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
