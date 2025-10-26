ARG BUILD_FROM
FROM $BUILD_FROM

# Install required packages
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-requests \
    docker-cli \
    iputils

# Create app directory
WORKDIR /app

# Copy Python script
COPY esphome_smart_updater.py /app/
RUN chmod +x /app/esphome_smart_updater.py

# Copy run script
COPY run.sh /
RUN chmod +x /run.sh

# Set entrypoint
CMD [ "/run.sh" ]
