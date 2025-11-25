# Configuration Guide

## Operating Modes

### 🔄 Normal Mode
**Use for:** Regular updates after initial setup
- Only processes devices where deployed_version ≠ current_version
- Compiles and uploads changed devices
- Fast and efficient

### 🔧 Repair Mode
**Use for:** One-time metadata rebuild
- Compiles all devices to populate storage files
- **NO OTA uploads** - compile-only operation
- Run this first if devices show "no deployed version"

### 📤 Upload Only Mode
**Use for:** Installing pre-compiled binaries
- Uses existing compiled binaries from Repair mode
- Skips compilation entirely
- Just performs OTA uploads
- Much faster than Normal mode for bulk operations

---

## Typical Workflow

**First Time Setup:**
1. Set `mode: repair` → Compiles all, populates metadata (~2-3 hours for 389 devices)
2. Set `mode: upload_only` + `update_when_version_matches: true` → Uploads all (~3-4 hours)
3. Set `mode: normal` → Future smart updates (minutes)

**Regular Use:**
- `mode: normal` → Only updates devices that need it

---

## Configuration Options

### Device Filtering
- **device_name_patterns:** Include only matching devices (e.g., `ai*`, `bedroom-*`)
- **skip_device_name_patterns:** Exclude matching devices (e.g., `test-*`, `offline-*`)

### Log Levels
- **quiet:** ~50 lines for 389 devices (minimal output)
- **normal:** ~200 lines (standard operation)
- **verbose:** ~1000 lines (detailed info)
- **debug:** Everything (for troubleshooting)

*Note: Full logs always saved to `/config/esphome_smart_update.log`*

### Force Updates
- **update_when_no_deployed_version:** Update new devices without metadata
- **update_when_version_matches:** Force update even when versions match
  - *Use with upload_only mode to install all binaries*
  - *Use with normal mode for bulk reinstalls*

### Testing
- **dry_run:** Preview what would be updated without actually doing it

### Error Handling
- **stop_on_compilation_error:** Stop if any compilation fails (recommended)
- **stop_on_upload_error:** Stop if any upload fails (recommended)

### Housekeeping
- **clear_log_on_start:** Clear log file on every start
- **clear_progress_on_start:** Clear progress tracking (restart from device #1)

---

## Quick Examples

**Test on 3 devices:**
```yaml
mode: normal
device_name_patterns: ["ai001", "ai002", "ai003"]
log_level: verbose
dry_run: true
```

**Repair all devices:**
```yaml
mode: repair
log_level: normal
```

**Upload all binaries:**
```yaml
mode: upload_only
update_when_version_matches: true
log_level: normal
```

**Daily updates (quiet logs):**
```yaml
mode: normal
log_level: quiet
```