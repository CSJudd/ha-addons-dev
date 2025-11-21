ARG BUILD_FROM
FROM $BUILD_FROM

# Install required packages
RUN apk add --no-cache \
    bash \
    coreutils \
    findutils \
    jq \
    tzdata

# Copy run script
COPY run.sh /
RUN chmod a+x /run.sh

# Set working directory
WORKDIR /

# Run the script
CMD ["/run.sh"]