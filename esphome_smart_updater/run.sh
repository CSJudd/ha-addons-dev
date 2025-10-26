#!/usr/bin/with-contenv bashio
set -euo pipefail

log_info()  { echo "[INFO] $*"; }
log_warn()  { echo "[WARN] $*"; }
log_fatal() { echo "[FATAL] $*"; exit 1; }

log_info "ESPHome Smart Updater starting..."

# Read options we care about here
COMPILE_MODE="$(bashio::config 'compile_mode')"
ESPHOME_CONTAINER="$(bashio::config 'esphome_container')"

# Detect docker socket (if the user enabled docker_api in config.json)
detect_docker() {
  for s in /run/docker.sock /var/run/docker.sock; do
    if [ -S "$s" ]; then
      echo "$s"
      return 0
    fi
  done
  return 1
}

DOCKER_SOCKET=""
if DOCKER_SOCKET="$(detect_docker)"; then
  export DOCKER_HOST="unix://${DOCKER_SOCKET}"
  log_info "Docker socket detected at: ${DOCKER_SOCKET}"
else
  if [ "${COMPILE_MODE}" = "docker" ]; then
    log_fatal "compile_mode=docker but no Docker socket found. Set 'docker_api': true and restart."
  else
    log_info "No Docker socket present; will use built-in ESPHome compiler."
  fi
fi

# If docker is present and desired, quick sanity
if [ -n "${DOCKER_SOCKET}" ] && [ "${COMPILE_MODE}" != "builtin" ]; then
  if ! command -v docker >/dev/null 2>&1; then
    log_warn "docker-cli not found; falling back to built-in compiler."
    DOCKER_SOCKET=""
  else
    if ! docker ps >/dev/null 2>&1; then
      log_warn "Cannot talk to Docker via ${DOCKER_HOST}; falling back to built-in compiler."
      DOCKER_SOCKET=""
    else
      # Verify the ESPHome container exists when in docker/auto mode
      if [ "${COMPILE_MODE}" != "builtin" ]; then
        if ! docker inspect "${ESPHOME_CONTAINER}" >/dev/null 2>&1; then
          log_warn "ESPHome container '${ESPHOME_CONTAINER}' not found; falling back to built-in compiler."
          DOCKER_SOCKET=""
        else
          log_info "Will compile via docker exec into '${ESPHOME_CONTAINER}'."
        fi
      fi
    fi
  fi
fi

# Prepare built-in venv if we don't have a working docker path
if [ -z "${DOCKER_SOCKET}" ] || [ "${COMPILE_MODE}" = "builtin" ]; then
  VENV_DIR="/data/venv"
  ESPHOME_BIN="${VENV_DIR}/bin/esphome"

  if [ ! -x "${ESPHOME_BIN}" ]; then
    log_info "Setting up built-in ESPHome venv at ${VENV_DIR} (first-run only)..."
    python3 -m venv "${VENV_DIR}"
    # shellcheck disable=SC1091
    . "${VENV_DIR}/bin/activate"
    # Install ESPHome in the venv. This is isolated, PEP 668-compliant.
    pip install --upgrade pip
    pip install "esphome==2025.10.3"
    deactivate
    log_info "Built-in ESPHome installed."
  else
    log_info "Built-in ESPHome venv already present."
  fi

  export ESPHOME_BIN
  log_info "Will compile via built-in ESPHome: ${ESPHOME_BIN}"
fi

# Export mode vars for Python
export SMART_UPDATER_MODE="$( [ -n "${DOCKER_SOCKET}" ] && [ "${COMPILE_MODE}" != "builtin" ] && echo docker || echo builtin )"
export SMART_UPDATER_ESPHOME_CONTAINER="${ESPHOME_CONTAINER}"

exec python3 /app/esphome_smart_updater.py