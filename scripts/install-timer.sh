#!/usr/bin/env bash
# Instala el timer de systemd que reconstruye la imagen cada noche (04:30).
# Uso: ./scripts/install-timer.sh   (pide sudo)
set -euo pipefail

cd "$(dirname "$0")/.."
project_dir="$(pwd)"
run_user="${SUDO_USER:-$USER}"

for unit in clipo-rebuild.service clipo-rebuild.timer; do
  sed -e "s#__CLIPO_DIR__#${project_dir}#g" -e "s#__CLIPO_USER__#${run_user}#g" \
    "deploy/${unit}" | sudo tee "/etc/systemd/system/${unit}" >/dev/null
done

sudo systemctl daemon-reload
sudo systemctl enable --now clipo-rebuild.timer
systemctl list-timers clipo-rebuild.timer --no-pager
