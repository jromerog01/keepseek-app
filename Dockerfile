# syntax=docker/dockerfile:1.7

# ---------- 1) Compilar la PWA ----------
FROM node:22-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---------- 2) Runtime: FastAPI + yt-dlp + ffmpeg + Deno ----------
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DATA_DIR=/data \
    STATIC_DIR=/app/static \
    HOME=/data \
    XDG_CACHE_HOME=/data/cache \
    DENO_DIR=/data/cache/deno

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# yt-dlp necesita un runtime de JavaScript para resolver los retos de YouTube
COPY --from=denoland/deno:bin /deno /usr/local/bin/deno

WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

# Cambiar este ARG invalida solo esta capa y las siguientes: es lo que usa
# scripts/rebuild.sh cada noche para traer el yt-dlp nightly más reciente.
ARG YTDLP_CACHE_BUST=dev
RUN echo "yt-dlp build: ${YTDLP_CACHE_BUST}" \
    && pip install -U --pre "yt-dlp[default,curl-cffi]" \
    && python -c "import yt_dlp.version as v; print('yt-dlp', v.__version__)"

COPY backend/app ./app
COPY --from=frontend /build/dist ./static

RUN useradd --uid 1000 --no-create-home clipo \
    && mkdir -p /data \
    && chown clipo:clipo /data
USER clipo
VOLUME /data
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"

# 1 solo worker: la cola de descargas vive en la memoria del proceso
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
