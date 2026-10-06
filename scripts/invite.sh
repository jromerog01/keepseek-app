#!/usr/bin/env bash
# Gestiona accesos temporales para que amigos prueben Clipo.
#   ./scripts/invite.sh crear "Ana" 7     -> token válido 7 días
#   ./scripts/invite.sh listar
#   ./scripts/invite.sh revocar <id>
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
BASE="http://127.0.0.1:${CLIPO_PORT:-8010}/api/invites"
AUTH=(-H "X-API-Key: ${API_TOKEN}")

case "${1:-}" in
  crear)
    label="${2:?Falta el nombre}"; days="${3:-7}"
    curl -fsS "${AUTH[@]}" -H 'Content-Type: application/json' \
      -d "{\"label\":\"${label}\",\"days\":${days}}" "$BASE"; echo ;;
  listar) curl -fsS "${AUTH[@]}" "$BASE"; echo ;;
  revocar) curl -fsS -X DELETE "${AUTH[@]}" "${BASE}/${2:?Falta el id}" && echo "Revocado" ;;
  *) echo "Uso: $0 crear <nombre> [días] | listar | revocar <id>"; exit 1 ;;
esac
