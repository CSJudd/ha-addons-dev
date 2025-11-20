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

# Check if ESPHome add-on is running
if ! docker ps --format '{{.Names}}' | grep -q "addon_5c53de3b_esphome"; then
  log_fatal "ESPHome add-on is not running. Please start it first."
fi

log_info "Configuration validated successfully"

# ============================================================================
# Environment Setup
# ============================================================================

log_info "Setting up environment..."

# Export add-on version for Python script
export ADDON_VERSION="${BASHIO_ADDON_VERSION:-unknown}"

log_info "Add-on version: ${ADDON_VERSION}"

# ============================================================================
# Execute Main Script
# ============================================================================

log_info "Starting Python script..."
log_info ""

exec python3 /app/esphome_smart_updater.py