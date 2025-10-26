# syntax=docker/dockerfile:1

ARG BUILD_FROM
FROM ${BUILD_FROM}

SHELL ["/bin/ash", "-o", "pipefail", "-c"]

# Runtime deps:
# - python3 (venv creation + runtime)
# - py3-requests for OTA
# - curl/jq for basic checks
# - iputils for ping
# - docker-cli only if user wants docker mode (lightweight)
RUN apk add --no-cache \
      python3 \
      py3-requests \
      python3-venv \
      curl \
      jq \
      iputils \
      docker-cli

ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY esphome_smart_updater.py /app/esphome_smart_updater.py
COPY run.sh /run.sh

RUN chmod +x /run.sh

CMD [ "/run.sh" ]