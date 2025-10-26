# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2025-10-25

### Added
- Initial release of ESPHome Smart Updater add-on
- Smart update logic: only updates devices where deployed_version ≠ current_version
- Offline device detection via ping
- Resume capability with progress tracking
- Comprehensive logging to `/config/esphome_smart_update.log`
- Configurable options for OTA password, offline handling, and update delays
- Support for all ESPHome device types
- Handles 375+ devices efficiently
- Integration with Home Assistant automations and scripts
- Multi-architecture support (armhf, armv7, aarch64, amd64, i386)

### Features
- HTTP OTA updates for all ESPHome devices
- Compilation inside ESPHome container
- Progress file for interrupted update recovery
- Detailed statistics reporting
- Configurable delay between updates
- Skip offline devices option


[1.0.1]
 - installs the Docker client in the add-on,
 - binds to the Supervisor’s socket at /run/docker.sock,
 - exports DOCKER_HOST=unix:///run/docker.sock,
 - adds a configurable ESPHome container name (defaults to the official add-on container: addon_15ef4d2f_esphome),
 - keeps everything else you described (logging, resume, skip offline, delay).


[1.0.2] - 2025-10-26
Fixed
- Resolve build failure on Alpine 3.19 due to PEP 668 by replacing pip install with APK package (py3-requests).