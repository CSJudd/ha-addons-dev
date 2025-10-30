# syntax=docker/dockerfile:1

###############################################################################
# Home Assistant Add-on: ESPHome Smart Updater
# Purpose: Safely compiles and updates ESPHome devices using the official
#          ESPHome container via Docker exec. Requires docker_api=true.
###############################################################################

# Always include a default BUILD_FROM, otherwise Supervisor won't mount /run/docker.sock
ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:3.19
FROM ${BUILD_FROM}

# ← NEW: accept the version the Supervisor passes (see logs: --build-arg BUILD_VERSION=...)
ARG BUILD_VERSION
# ← NEW: make it available at runtime for version-change housekeeping
ENV ADDON_VERSION=${BUILD_VERSION:-unknown}

# Keep consistent shell and fail fast on any errors
SHELL ["/bin/ash", "-o", "pipefail", "-c"]

# Install runtime dependencies
RUN apk add --no-cache \
      python3 \
      py3-requests \
      docker-cli \
      iputils \
      curl \
      jq

# Environment and working directory setup
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Copy main scripts
COPY esphome_smart_updater.py /app/esphome_smart_updater.py
COPY run.sh /run.sh
RUN chmod +x /run.sh

# Entry point
CMD ["/run.sh"]