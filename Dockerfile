FROM ghcr.io/astral-sh/uv:0.11.21@sha256:ff07b86af50d4d9391d9daf4ff89ce427bc544f9aae87057e69a1cc0aa369946 AS uv
FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b

COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
RUN uv sync --locked --no-dev --no-editable --python /usr/local/bin/python \
    && rm -rf /root/.cache/uv
USER 10001:10001
CMD ["/app/.venv/bin/python", "-m", "mcwl_tg_manager"]
