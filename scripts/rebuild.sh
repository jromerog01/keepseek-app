#!/usr/bin/env bash
# Reconstruye la imagen de Clipo con el yt-dlp nightly más reciente.
# Lo ejecuta el timer de systemd cada noche (ver deploy/ e install-timer.sh).
set -euo pipefail

cd "$(dirname "$0")/.."
log() { echo "[clipo-rebuild $(date -Is)] $*"; }

mkdir -p data

# Espera (máx. 30 min) a que no haya descargas activas para no interrumpirlas.
for _ in $(seq 1 180); do
  active=$(curl -fsS --max-time 5 http://127.0.0.1:8000/api/health 2>/dev/null \
    | grep -o '"active_jobs":[0-9]*' | cut -d: -f2 || true)
  if [ -z "${active:-}" ] || [ "$active" = "0" ]; then
    break
  fi
  log "hay $active descarga(s) activa(s), esperando..."
  sleep 10
done

export YTDLP_CACHE_BUST="$(date +%Y%m%d%H%M)"

log "construyendo imagen (yt-dlp nightly)..."
docker compose build --pull clipo

log "reiniciando contenedor..."
docker compose up -d clipo

log "limpiando imágenes viejas..."
docker image prune -f >/dev/null

for _ in $(seq 1 30); do
  status=$(docker inspect --format '{{.State.Health.Status}}' clipo 2>/dev/null || echo unknown)
  [ "$status" = "healthy" ] && break
  sleep 2
done
log "estado del contenedor: $status"
log "versión de yt-dlp: $(docker compose exec -T clipo python -c 'import yt_dlp.version as v; print(v.__version__)')"
