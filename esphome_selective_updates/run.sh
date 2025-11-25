#!/usr/bin/with-contenv bashio
set -euo pipefail

# ============================================================================
# ESPHome Selective Updates - Startup Script
# ============================================================================

LOG_FILE="/config/esphome_smart_update.log"

# ============================================================================
# Pre-flight Log Clearing (BEFORE any other logging)
# ============================================================================

handle_log_clearing() {
  local clear_on_start="$(bashio::config 'clear_log_on_start')"
  local clear_now="$(bashio::config 'clear_log_now')"
  
  if [ "${clear_on_start}" = "true" ]; then
    if [ -f "${LOG_FILE}" ]; then
      : > "${LOG_FILE}"
      echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] Log file cleared (clear_log_on_start)"
    fi
  fi
  
  if [ "${clear_now}" = "true" ]; then
    if [ -f "${LOG_FILE}" ]; then
      : > "${LOG_FILE}"
      echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] Log file cleared (clear_log_now)"
    fi
  fi
}

# Clear log BEFORE any other operations
handle_log_clearing

# ============================================================================
# Standard logging functions
# ============================================================================

log_info()  { echo "[INFO] $*"; }
log_warn()  { echo "[WARN] $*"; }
log_fatal() { echo "[FATAL] $*"; exit 1; }

# ============================================================================
# Banner
# ============================================================================

log_info "======================================================================"
log_info "ESPHome Selective Updates - Starting"
log_info "======================================================================"

# ============================================================================
# Configuration Validation
# ============================================================================

log_info "Validating configuration..."

# Check if ESPHome directory exists
if [ ! -d "/config/esphome" ]; then
  log_fatal "ESPHome directory not found at /config/esphome"
fi

# ============================================================================
# ESPHome Container Detection (IMPROVED)
# ============================================================================

log_info "Detecting ESPHome container..."

# Try multiple detection methods
ESPHOME_CONTAINER=""

# Method 1: Standard addon pattern - but EXCLUDE our own container
ESPHOME_CONTAINER=$(docker ps --format '{{.Names}}' | grep -E "addon_.*_esphome" | grep -v "esphome_selective_updates" | head -n 1 || true)

if [ -z "${ESPHOME_CONTAINER}" ]; then
  log_info "Trying alternative container name pattern..."
  # Method 2: Try hassio pattern
  ESPHOME_CONTAINER=$(docker ps --format '{{.Names}}' | grep -E "hassio.*esphome" | grep -v "selective_updates" | head -n 1 || true)
fi

if [ -z "${ESPHOME_CONTAINER}" ]; then
  log_info "Trying generic esphome pattern..."
  # Method 3: Any container with esphome in the name, but NOT us
  ESPHOME_CONTAINER=$(docker ps --format '{{.Names}}' | grep -i "esphome" | grep -v "selective_updates" | head -n 1 || true)
fi

if [ -z "${ESPHOME_CONTAINER}" ]; then
  log_fatal "ESPHome add-on is not running. Please start it first.

Available running containers:
$(docker ps --format '{{.Names}}')

Please ensure the ESPHome add-on is started before running this add-on."
fi

log_info "Found ESPHome container: ${ESPHOME_CONTAINER}"

# Verify the container is actually running
if ! docker ps --filter "name=${ESPHOME_CONTAINER}" --format "{{.Names}}" | grep -q "${ESPHOME_CONTAINER}"; then
  log_fatal "Container '${ESPHOME_CONTAINER}' exists but is not running"
fi

# Test if we can exec into the container
if ! docker exec "${ESPHOME_CONTAINER}" echo "Connection test" >/dev/null 2>&1; then
  log_fatal "Cannot execute commands in container '${ESPHOME_CONTAINER}'"
fi

log_info "✓ Container connectivity verified"

export ESPHOME_CONTAINER

log_info "Configuration validated successfully"

# ============================================================================
# Environment Setup
# ============================================================================

log_info "Setting up environment..."

# Export add-on version for Python script
# Try Bashio first, fall back to Dockerfile version
export ADDON_VERSION="${BASHIO_ADDON_VERSION:-2.0.12a}"

log_info "Add-on version: ${ADDON_VERSION}"

# ============================================================================
# Execute Main Script
# ============================================================================

log_info "Starting Python script..."
log_info ""

exec python3 /app/esphome_smart_updater.py