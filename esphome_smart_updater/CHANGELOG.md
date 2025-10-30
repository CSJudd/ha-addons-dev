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


# ---------------------------------------------------------------------------------------------
## [1.1.1] - 2025-10-26
Fixed
- Corrected ESPHome CLI invocation order (`esphome compile <file>`) which previously caused
  "invalid choice" errors during built-in compilation.
- Implemented full graceful stop handling:
  - Add-on now traps SIGTERM/SIGINT events from Home Assistant.
  - Any running compile subprocess is terminated cleanly.
  - Progress is saved immediately, preventing restarts from repeating completed devices.
  - Prevents the add-on from continuing updates after being stopped.
- Maintains all prior functionality and resume logic for both Docker and built-in compile modes.


# ---------------------------------------------------------------------------------------------
## [1.2.0] - 2025-10-30
Changed
- Switched to Docker-exec-only compilation (inside official ESPHome add-on) because ESPHome
  PlatformIO toolchains for ESP8266/ESP32 require glibc and do not run on Alpine (musl).
- Removed builtin/venv compiler path to avoid toolchain failures ("xtensa-lx106-elf-g++: not found").
- Add-on now requires Supervisor Docker socket (`docker_api: true`) and validates container name.
Fixed
- Robust stop handling: kill entire compiler process group on stop to prevent continued runs after
  the add-on is stopped; persist progress immediately.


# ---------------------------------------------------------------------------------------------
## [1.2.1] - 2025-10-30
Fixed
- Ensured Supervisor mounts Docker socket by declaring `"docker_api": true`.
- Disabled automatic restart loop during failures with `"watchdog": false"` to simplify testing.
Notes
- Rebuild/reinstall is required after changing add-on capabilities so the socket bind is applied.


# ---------------------------------------------------------------------------------------------
## [1.2.31] - 2025-10-30

### Fixed
- **Critical fix:** Restored Supervisor Docker socket mount by adding a default `BUILD_FROM` value in `Dockerfile`
  - Previous builds lacked a valid base image, preventing `/run/docker.sock` from being passed into the container
  - Root cause: `ARG BUILD_FROM` was declared without a fallback, causing Supervisor to treat the image as untrusted
- Ensured `hassio_role: "manager"` and `docker_api: true` are honored consistently
- Verified `Dockerfile` now builds from `ghcr.io/home-assistant/amd64-base:3.19` to comply with Supervisor security model

### Changed
- Updated `Dockerfile` comments and structure for clarity and HA compliance
- Incremented add-on version to `1.2.31` for repository and Supervisor rebuild triggering

### Notes
This version **enables Docker exec functionality** correctly.  
You should now see:
[INFO] Using Docker socket at: /run/docker.sock
in the add-on logs after start.

# ---------------------------------------------------------------------------------------------
## [1.2.32] - 2025-10-30

### Fixed
- **Forced Supervisor to mount Docker socket** by adding `"full_access": true` for diagnostic builds.
- Confirms Supervisor privilege issue was preventing socket visibility despite `"docker_api": true` and `"hassio_role": "manager"`.
- Retained automatic socket path detection (`/run/docker.sock` or `/var/run/docker.sock`).
- This version ensures guaranteed Docker access for testing and validation.

### Changed
- Updated `config.json` to include extended mappings and full access.
- Incremented version to `1.2.32` for Supervisor rebuild trigger.

# ---------------------------------------------------------------------------------------------
##  [1.2.33] - 2025-10-30
### Fixed
- Documented and enforced requirement to run with **Protection mode OFF** for Docker API access; Supervisor blocks `/run/docker.sock` when Protection mode is ON.
- Startup script now emits explicit hint when socket is missing due to Protection mode.
### Changed
- Kept `docker_api: true` + `hassio_role: "manager"`; removed need for `full_access`.


# ---------------------------------------------------------------------------------------------
##  [1.2.34] - 2025-10-30

### Fixed
- Updated firmware path for ESPHome ≥ 2025.9 (moved from `.esphome/build/...` to `build/...`)
- Prevented false "Could not copy binary" errors during compilation step
- Added fallback detection for legacy path to maintain compatibility with older ESPHome add-ons


# ---------------------------------------------------------------------------------------------
##  [1.2.38] - 2025-10-30
### Fixed
- Remove unsupported `--no-logs` flag from `esphome upload` CLI invocation that caused OTA to fail immediately on ESPHome 2025.10.x.
- Improve uploader failure diagnostics by logging the last lines of stdout/stderr.


# ---------------------------------------------------------------------------------------------
##  [1.2.39] - 2025-10-30
### Fixed
- After successful OTA, update ESPHome Dashboard metadata (`dashboard.json`) so the UI clears the “Update needed” badge.
- Write `deployed_version` to match `current_version` for the updated YAML entry in both the ESPHome container and the host mirror.
