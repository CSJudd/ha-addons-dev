# HAOS Maintenance Cleaner

A Home Assistant add-on for automatically cleaning up ESPHome build artifacts, Docker logs, Supervisor logs, and Home Assistant logs on Home Assistant OS.

## Features

- 🧹 **ESPHome Cleanup**: Automatically removes build artifacts, caches, and temporary files
- 🐳 **Docker Log Management**: Truncates container logs to prevent disk bloat
- 📋 **Supervisor Log Rotation**: Keeps only the last N lines of supervisor logs
- 📝 **HA Log Cleanup**: Removes old rotated Home Assistant logs
- ⏰ **Flexible Scheduling**: Run on startup, daily at a specific time, or both
- 🔍 **Auto-Discovery**: Automatically finds your ESPHome add-on
- 📊 **Space Reporting**: Shows disk space freed by each cleanup operation

## Installation

1. Navigate to **Settings** → **Add-ons** → **Add-on Store** in Home Assistant
2. Click the menu (⋮) in the top right and select **Repositories**
3. Add this repository URL: `https://github.com/yourusername/haos-maintenance-cleaner`
4. Find "HAOS Maintenance Cleaner" in the add-on store and click **Install**

### Local Installation

1. Copy this folder to `/addons/haos_maintenance_cleaner` in your Home Assistant config
2. Restart Home Assistant or reload add-ons
3. Install from the local add-ons section

## Configuration
```yaml
schedule_enabled: true          # Enable scheduled cleanup
cleanup_time: "03:30"           # Daily cleanup time (HH:MM format, 24-hour)
run_on_startup: true            # Run cleanup when add-on starts

cleanup_esphome: true           # Clean ESPHome build artifacts
cleanup_docker_logs: true       # Truncate Docker container logs
cleanup_supervisor_log: true    # Clean supervisor log
supervisor_log_lines: 10000     # Keep last N lines (0 = truncate completely)
cleanup_ha_logs: true           # Clean old HA rotated logs
ha_log_retention_days: 7        # Delete logs older than N days (0 = delete all)
```

## What Gets Cleaned

### ESPHome Artifacts
- `/config/esphome/.esphome/build`
- `/config/esphome/.esphome/.pioenvs`
- `/config/esphome/.esphome/.platformio`
- `/config/esphome/.esphome/managed_components`
- `/config/esphome/.esphome/managed_libraries`
- Auto-discovered ESPHome add-on data: `build/`, `cache/`, `packages/`

### Docker Logs
- All `*-json.log` files in `/mnt/data/docker/containers/*/*`
- Files are truncated (not deleted) to preserve container logging

### Supervisor Logs
- `/mnt/data/supervisor/supervisor.log`
- Keeps last N lines (configurable)

### Home Assistant Logs
- `/config/home-assistant.log.*` (rotated logs)
- Deletes files older than N days (configurable)

## Support

For issues, feature requests, or contributions, visit: https://github.com/yourusername/haos-maintenance-cleaner

## License

MIT License - See LICENSE file for details

---

**May your disk space be forever plentiful, and your logs forever manageable.** 🔥