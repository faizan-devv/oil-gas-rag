FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

# Dependencies first, so editing the code does not reinstall them.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY data/raw ./data/raw
RUN uv sync --frozen --no-dev

# The vector index is built on first start and written here.
RUN useradd --create-home appuser && mkdir -p data/index && chown -R appuser /app/data
USER appuser

EXPOSE 8000
# Model endpoints and keys come from the environment (--env-file .env); none are baked in.
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
