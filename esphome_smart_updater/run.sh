#!/usr/bin/with-contenv bashio
set -euo pipefail

bashio::log.info "ESPHome Smart Updater starting..."

# Confirm Docker API access was granted and socket is mounted
if [ ! -S "/run/docker.sock" ]; then
  bashio::log.fatal "Docker socket '/run/docker.sock' not found. In the add-on config, 'docker_api' must be true."
  exit 1
fi

# Ensure DOCKER_HOST is correct (Supervisor uses /run/docker.sock)
export DOCKER_HOST="${DOCKER_HOST:-unix:///run/docker.sock}"

# Basic sanity: docker client present?
if ! command -v docker >/dev/null 2>&1; then
  bashio::log.fatal "Docker client not found. Image must include docker-cli."
  exit 1
fi

# Let the Python handle all logic
exec python3 /app/esphome_smart_updater.py