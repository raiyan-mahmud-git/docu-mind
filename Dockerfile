FROM python:3.12-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.12-slim-bookworm AS runtime

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONPATH="/app/src" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME="/home/documind/.cache/huggingface" \
    DOCUMIND_DATA_DIR="/app/data" \
    DOCUMIND_UPLOAD_DIR="/app/data/uploads" \
    DOCUMIND_CHROMA_DIR="/app/data/chroma" \
    DOCUMIND_SQLITE_PATH="/app/data/documind.sqlite3" \
    DOCUMIND_OCR_TESSDATA="/usr/share/tesseract-ocr/5/tessdata"

RUN apt-get update \
    && apt-get install --no-install-recommends -y libgomp1 tesseract-ocr tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --create-home --shell /usr/sbin/nologin documind \
    && mkdir -p /app/data /home/documind/.cache/huggingface \
    && chown -R documind:documind /app/data /home/documind/.cache

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --chown=documind:documind src/ ./src/
COPY --chown=documind:documind web/ ./web/

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]

CMD ["python", "-m", "uvicorn", "documind.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
