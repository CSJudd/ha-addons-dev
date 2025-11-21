# Changelog

## [1.0.0] - 2025-11-21

### Added
- Initial release of HAOS Maintenance Cleaner
- Auto-discovery of ESPHome add-on slug
- ESPHome build artifact cleanup (config and add-on data)
- Docker container log truncation
- Supervisor log rotation with configurable line retention
- Home Assistant rotated log cleanup with configurable day retention
- Scheduled cleanup with configurable daily time
- On-demand cleanup on add-on startup
- Granular enable/disable flags for each cleanup category
- Disk space before/after calculations with human-readable output
- Color-coded logging for easy monitoring