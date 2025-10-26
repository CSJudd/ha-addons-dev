#!/usr/bin/with-contenv bashio
set -euo pipefail

bashio::log.info "ESPHome Smart Updater starting..."

# Auto-detect Docker socket path used by Supervisor
SOCKET=""
if [ -S "/run/docker.sock" ]; then
  SOCKET="/run/docker.sock"
elif [ -S "/var/run/docker.sock" ]; then
  SOCKET="/var/run/docker.sock"
fi

if [ -z "${SOCKET}" ]; then
  bashio::log.fatal "No Docker socket found. Ensure 'docker_api': true in config.json and restart the add-on."
  exit 1
fi

export DOCKER_HOST="unix://${SOCKET}"
bashio::log.info "Using Docker socket at: ${SOCKET}"

# Sanity: docker client present?
if ! command -v docker >/dev/null 2>&1; then
  bashio::log.fatal "Docker client not found in image. (Expected docker-cli)."
  exit 1
fi

# Sanity: can we talk to Docker?
if ! docker ps >/dev/null 2>&1; then
  bashio::log.fatal "Cannot talk to Docker via ${DOCKER_HOST}. Check Supervisor permissions and 'docker_api': true."
  exit 1
fi

# Hand off to Python
exec python3 /app/esphome_smart_updater.py