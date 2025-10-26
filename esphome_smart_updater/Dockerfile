# syntax=docker/dockerfile:1

ARG BUILD_FROM
FROM ${BUILD_FROM}

SHELL ["/bin/ash", "-o", "pipefail", "-c"]

# Runtime deps:
# - python3 + py3-requests (HTTP OTA)
# - py3-virtualenv + py3-pip (to create a venv WITH pip inside)
# - curl/jq/iputils (helpers)
# - docker-cli (only used if compile_mode uses docker)
RUN apk add --no-cache \
      python3 \
      py3-requests \
      py3-virtualenv \
      py3-pip \
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