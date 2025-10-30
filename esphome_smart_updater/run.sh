#!/usr/bin/with-contenv bashio
set -euo pipefail

log_info()  { echo "[INFO] $*"; }
log_fatal() { echo "[FATAL] $*"; exit 1; }

log_info "ESPHome Smart Updater starting (Docker exec mode)..."

ESPHOME_CONTAINER="$(bashio::config 'esphome_container')"

# Detect Supervisor Docker socket
SOCKET=""
for s in /run/docker.sock /var/run/docker.sock; do
  if [ -S "$s" ]; then SOCKET="$s"; break; fi
done
[ -n "$SOCKET" ] || log_fatal "No Docker socket mounted. Set 'docker_api': true in config.json and restart."

export DOCKER_HOST="unix://${SOCKET}"
log_info "Using Docker socket at: ${SOCKET}"

# Sanity checks
command -v docker >/dev/null 2>&1 || log_fatal "docker-cli missing in image."
docker ps >/dev/null 2>&1 || log_fatal "Cannot talk to Docker via ${DOCKER_HOST}."
docker inspect "${ESPHOME_CONTAINER}" >/dev/null 2>&1 || log_fatal "ESPHome container '${ESPHOME_CONTAINER}' not found. Adjust 'esphome_container' in options."

exec python3 /app/esphome_smart_updater.py