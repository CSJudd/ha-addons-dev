# syntax=docker/dockerfile:1
ARG BUILD_FROM
FROM ${BUILD_FROM}

SHELL ["/bin/ash", "-o", "pipefail", "-c"]

RUN apk add --no-cache \
      python3 \
      py3-requests \
      docker-cli \
      iputils \
      curl \
      jq

ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY esphome_smart_updater.py /app/esphome_smart_updater.py
COPY run.sh /run.sh
RUN chmod +x /run.sh

CMD ["/run.sh"]