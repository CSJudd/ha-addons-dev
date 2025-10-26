#!/usr/bin/with-contenv bashio

bashio::log.info "Starting ESPHome Smart Updater..."

# Log configuration
OTA_PASSWORD=$(bashio::config 'ota_password')
SKIP_OFFLINE=$(bashio::config 'skip_offline')
DELAY=$(bashio::config 'delay_between_updates')

bashio::log.info "Configuration loaded:"
bashio::log.info "  - OTA Password: ${OTA_PASSWORD:0:8}..."
bashio::log.info "  - Skip Offline: $SKIP_OFFLINE"
bashio::log.info "  - Delay Between Updates: ${DELAY}s"

# Execute the Python script
python3 /app/esphome_smart_updater.py

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    bashio::log.info "Update process completed successfully"
else
    bashio::log.error "Update process failed with exit code $EXIT_CODE"
fi

exit $EXIT_CODE
