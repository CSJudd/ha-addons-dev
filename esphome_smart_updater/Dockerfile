# syntax=docker/dockerfile:1

# Home Assistant add-on base (Alpine-based 3.19 images)
ARG BUILD_FROM
FROM ${BUILD_FROM}

# Make shell sane
SHELL ["/bin/ash", "-o", "pipefail", "-c"]

# Install runtime deps:
# - python3 + pip for the updater
# - docker-cli to talk to Supervisor's docker via socket
# - iputils for ping
# - curl/jq for simple API checks if needed
RUN apk add --no-cache \
      python3 \
      py3-pip \
      docker-cli \
      iputils \
      curl \
      jq \
  && pip3 install --no-cache-dir requests

# Ensure Python is default
ENV PYTHONUNBUFFERED=1

# IMPORTANT: point docker client at HA's socket
ENV DOCKER_HOST=unix:///run/docker.sock

# Workdir & files
WORKDIR /app
COPY esphome_smart_updater.py /app/esphome_smart_updater.py
COPY run.sh /run.sh

# Entrypoint script
RUN chmod +x /run.sh

# Start
CMD [ "/run.sh" ]