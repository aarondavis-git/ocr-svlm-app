# syntax=docker/dockerfile:1
FROM python:3.14-slim

# System programs: Tesseract with German, Poppler for PDFs, a library OpenCV needs
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-deu poppler-utils libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# uv, copied from its official image (same version as on your Mac)
COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 1) Dependencies only: this slow layer is cached until pyproject.toml/uv.lock change
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# 2) The app itself
COPY README.md ./
COPY .streamlit ./.streamlit
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Don't run as root
RUN useradd --create-home app
USER app

ENV PATH="/app/.venv/bin:$PATH" \
    LMSTUDIO_BASE_URL=http://host.docker.internal:1234/v1 \
    DEFAULT_VLM_MODEL=qwen/qwen3-vl-4b

EXPOSE 8501
CMD ["streamlit", "run", "src/review/app.py", \
    "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]