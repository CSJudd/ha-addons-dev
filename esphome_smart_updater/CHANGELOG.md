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
