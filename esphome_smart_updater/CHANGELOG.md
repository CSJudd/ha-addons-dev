# Changelog

All notable changes to this project will be documented in this file.

# ---------------------------------------------------------------------------------------------
## [1.0.0] - 2025-10-25
# -- Added
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

# -- Features
- HTTP OTA updates for all ESPHome devices
- Compilation inside ESPHome container
- Progress file for interrupted update recovery
- Detailed statistics reporting
- Configurable delay between updates
- Skip offline devices option

# ---------------------------------------------------------------------------------------------
## [1.0.1] - 2025-10-26
 - installs the Docker client in the add-on,
 - binds to the Supervisor’s socket at /run/docker.sock,
 - exports DOCKER_HOST=unix:///run/docker.sock,
 - adds a configurable ESPHome container name (defaults to the official add-on container: addon_15ef4d2f_esphome),
 - keeps everything else you described (logging, resume, skip offline, delay).

# ---------------------------------------------------------------------------------------------
## [1.0.2] - 2025-10-26
Fixed
- Resolve build failure on Alpine 3.19 due to PEP 668 by replacing pip install with APK package (py3-requests).

# ---------------------------------------------------------------------------------------------
## [1.0.3] - 2025-10-26
Fixed
- Robust Docker socket detection: supports both /run/docker.sock and /var/run/docker.sock.
- Removed hardcoded DOCKER_HOST from config; now set dynamically in entrypoint.
- Keeps Alpine-only Python deps (py3-requests) to avoid PEP 668 issues.

# ---------------------------------------------------------------------------------------------
## [1.0.4] - 2025-10-26
Changed
- New compile strategy with automatic fallback:
  - If Docker socket + ESPHome container available: compile via `docker exec`.
  - Otherwise: compile locally inside add-on via a persistent venv at /data/venv (no Docker required).
- `docker_api` is now optional. Set `compile_mode` to control behavior: auto | docker | builtin.
- Zero hard-coded socket paths; no more startup crashes if Docker socket is absent.

# ---------------------------------------------------------------------------------------------
## [1.1.0] - 2025-10-26
Fixed
- Replace unavailable Alpine package `python3-venv` with `py3-virtualenv` and `py3-pip`.
- Venv creation now uses `python3 -m virtualenv /data/venv`, ensuring pip is available inside venv.
- Keeps docker-exec path optional; builtin compiler is default and resilient.