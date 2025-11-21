# ============================================================================
# ESPHome Selective Updates - Dockerfile
# ============================================================================
# Alpine Linux base image
# Uses Docker exec to compile firmware inside the official ESPHome container
# ============================================================================

ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:3.19
FROM ${BUILD_FROM}

# ============================================================================
# Install Dependencies
# ============================================================================
# Alpine packages needed:
# - python3: Run the main updater script
# - py3-requests: HTTP library (if needed in future)
# - docker-cli: Execute commands in ESPHome container
# - bash: Run shell script
# - iputils: Ping utility for offline detection (future feature)
# ============================================================================

RUN apk add --no-cache \
    python3 \
    py3-requests \
    docker-cli \
    bash \
    iputils

# ============================================================================
# Copy Add-on Files
# ============================================================================

WORKDIR /app

COPY esphome_smart_updater.py /app/esphome_smart_updater.py
COPY run.sh /app/run.sh

# ============================================================================
# Set Permissions
# ============================================================================

RUN chmod +x /app/run.sh && \
    chmod +x /app/esphome_smart_updater.py

# ============================================================================
# Set Environment Variables
# ============================================================================

ENV LANG=C.UTF-8
ENV ADDON_VERSION=2.0.4

# ============================================================================
# Entry Point
# ============================================================================

CMD ["/app/run.sh"]