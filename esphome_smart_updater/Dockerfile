# syntax=docker/dockerfile:1

ARG BUILD_FROM
FROM ${BUILD_FROM}

SHELL ["/bin/ash", "-o", "pipefail", "-c"]

# Install runtime deps:
# - python3 + py3-requests (no pip — avoids PEP 668 issues)
# - docker-cli to talk to Supervisor's docker via socket
# - iputils for ping, curl/jq for simple checks
RUN apk add --no-cache \
      python3 \
      py3-requests \
      docker-cli \
      iputils \
      curl \
      jq

# Make Python output unbuffered
ENV PYTHONUNBUFFERED=1

# IMPORTANT: point docker client at HA’s socket
ENV DOCKER_HOST=unix:///run/docker.sock

WORKDIR /app
COPY esphome_smart_updater.py /app/esphome_smart_updater.py
COPY run.sh /run.sh

RUN chmod +x /run.sh

CMD [ "/run.sh" ]