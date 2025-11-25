# ESPHome Selective Updates

**Smart bulk updates for ESPHome devices - only updates devices that actually need it**

---

## 🎯 Why This Add-on Exists

### The Problem

ESPHome's built-in "Update All" button has critical flaws:

- ❌ **No intelligence** - Recompiles ALL devices, even ones already updated
- ❌ **No resume** - If interrupted at device #200, starts over from #1
- ❌ **Wastes time** - Takes 10+ hours for 389 devices when only 5 need updates
- ❌ **No offline detection** - Tries to update unreachable devices and fails
- ❌ **Floods logs** - Thousands of log lines make troubleshooting impossible

### The Solution

This add-on fixes ESPHome's missing functionality:

- ✅ **Smart updates** - Only compiles devices where `deployed_version ≠ current_version`
- ✅ **Three operating modes** - Normal, Repair, Upload Only
- ✅ **Resume capability** - Picks up exactly where it left off if interrupted
- ✅ **Progress tracking** - Detailed logging and state persistence
- ✅ **Efficiency** - Minutes instead of hours for large deployments
- ✅ **Manageable logs** - Configurable log levels keep Supervisor logs clean

**Real-world results:** Updates 389 devices in ~30 minutes instead of 10+ hours, with logs you can actually read.

---

## 🎓 Who Should Use This

### ✅ **This add-on is for you if:**
- You have **50+ ESPHome devices**
- You're tired of ESPHome's "Update All" blindly recompiling everything
- You understand basic Docker concepts
- You're comfortable with "advanced user" tools
- You want control over logging verbosity

### ❌ **Don't use this if:**
- You only have a handful of devices (just use ESPHome dashboard manually)
- You're uncomfortable with the Protection Mode requirement (see below)
- You want a "set and forget" solution (this requires understanding)

---

## ⚠️ Important: Protection Mode Requirement

### **This add-on requires Protection Mode to be turned OFF**

**Why:**
- This add-on extends ESPHome's functionality
- It needs to compile firmware inside the ESPHome container
- This requires Docker socket access, which Protection Mode blocks

**Is this safe?**

Yes, because this add-on:
- ✅ **Only accesses the ESPHome add-on container** (not your host system)
- ✅ **Only reads/writes `/config/esphome/`** (same as ESPHome does)
- ✅ **Uses the same tools ESPHome uses** (esphome CLI, PlatformIO)
- ✅ **Doesn't access other containers** or privileged host resources
- ✅ **Open source** - you can audit the entire codebase

**What it does NOT do:**
- ❌ Does not access your Home Assistant container
- ❌ Does not modify system files
- ❌ Does not access other add-ons
- ❌ Does not expose network services
- ❌ Does not run background services

### How to Disable Protection Mode

1. Go to **Add-ons → ESPHome Selective Updates → Info tab**
2. Find **"Protection mode"** toggle
3. Turn it **OFF**
4. Restart the add-on

---

## 🚀 Features

### Three Operating Modes

**Normal Mode** - Smart updates for everyday use
- Only updates devices where deployed_version ≠ current_version
- Compiles and uploads changed devices
- Fast: processes only what's needed

**Repair Mode** - Rebuild metadata (one-time setup)
- Compiles all devices to populate storage files
- **NO OTA uploads** - compile-only
- Fixes missing metadata after ESPHome cleanup

**Upload Only Mode** - Install pre-compiled binaries
- Uses existing compiled binaries
- Skips compilation entirely
- Just performs OTA uploads
- Perfect after repair mode completes

### Additional Features

- **Configurable Logging** – Control log verbosity (quiet/normal/verbose/debug)
- **Resume Capability** – Tracks progress, can resume if interrupted
- **Dry Run Mode** – Preview what would be updated without actually updating
- **Device Filtering** – Process only specific devices or exclude problematic ones
- **Comprehensive Logging** – Full logs saved to `/config/esphome_smart_update.log`
- **Clean Supervisor Logs** – Manageable output in Home Assistant Logs tab
- **Integration Ready** – Trigger from Home Assistant automations or scripts
- **Bulk Processing** – Efficiently handles 389+ devices
- **Graceful Stop** – Handles interruptions, preserves progress

---

## 📋 Requirements

- Home Assistant OS or Supervisor
- Official **ESPHome** add-on installed and running
- Supervisor Docker socket access (`docker_api: true`, `hassio_role: "manager"`)
- **Protection Mode OFF** (see above)

---

## 🧩 Installation

### Step 1 – Add the Repository

1. Open **Settings → Add-ons → Add-on Store**
2. Click **⋮ → Repositories**
3. Add: `https://github.com/CSJudd/ha-addons-dev.git`
4. Click **Add**, then **Close**, then **Reload**

### Step 2 – Install the Add-on

1. Find **ESPHome Selective Updates**
2. Click **Install**
3. Wait for installation to complete

### Step 3 – Configure

The add-on now has a **user-friendly configuration interface** with dropdown menus and help text for every option.

#### Basic Configuration

```yaml
mode: normal  # Dropdown: Normal / Repair / Upload Only
device_name_patterns: []  # Optional: filter devices
skip_device_name_patterns: []  # Optional: exclude devices
log_level: normal  # Dropdown: quiet / normal / verbose / debug
update_when_version_matches: false  # Force updates even when versions match
dry_run: false  # Preview mode
```

#### Configuration Options Explained

| Option | Description |
|--------|-------------|
| **mode** | Operating mode: Normal (smart updates), Repair (rebuild metadata), Upload Only (install binaries) |
| **device_name_patterns** | Include only devices matching these patterns (e.g., `ai*`, `bedroom-*`). Empty = all devices |
| **skip_device_name_patterns** | Exclude devices matching these patterns (e.g., `test-*`, `offline-*`) |
| **log_level** | Log verbosity: quiet (~50 lines), normal (~200 lines), verbose (~1000 lines), debug (everything) |
| **update_when_no_deployed_version** | Update devices with no deployed version in metadata |
| **update_when_version_matches** | Force update even when versions match (useful after repair mode) |
| **dry_run** | Preview what would be updated without actually doing it |
| **stop_on_compilation_error** | Stop entire process if any device fails to compile |
| **stop_on_upload_error** | Stop entire process if any device fails to upload |
| **clear_log_on_start** | Clear log file every time the add-on starts |
| **clear_progress_on_start** | Clear progress tracking every start (forces restart from device #1) |

### Step 4 – Disable Protection Mode

**CRITICAL:** You must turn OFF Protection Mode or the add-on will not work.

1. Go to the **Info** tab
2. Find **"Protection mode"** toggle
3. Turn it **OFF**

### Step 5 – Start the Add-on

1. Go to the **Info** tab
2. Turn **Start on boot** OFF (recommended - run on-demand)
3. Click **Start**

Expected initial log lines:
```
======================================================================
ESPHome Selective Updates v2.0.12
======================================================================
Log level: normal

NORMAL MODE - Smart Updates

======================================================================
Discovering Devices
======================================================================
Discovered 389 ESPHome devices
```

---

## 🛠️ Usage Workflows

### Workflow 1: Initial Setup (Missing Metadata)

If your devices have no metadata (after ESPHome cleanup or fresh install):

**Step 1 - Repair Mode (~2-3 hours for 389 devices):**
```yaml
mode: repair
log_level: normal
```

Result: All devices compiled, storage metadata populated, **no uploads**

**Step 2 - Upload Only Mode (~3-4 hours for 389 devices):**
```yaml
mode: upload_only
update_when_version_matches: true
log_level: normal
```

Result: Pre-compiled binaries uploaded to all devices

**Step 3 - Normal Mode (ongoing - minutes):**
```yaml
mode: normal
log_level: quiet
```

Result: Only devices with version changes are updated

---

### Workflow 2: Regular Updates

For everyday use after initial setup:

```yaml
mode: normal
log_level: quiet
```

- Automatically detects devices that need updates
- Only processes changed devices
- Fast and efficient

---

### Workflow 3: Testing New Config

Test changes on specific devices:

```yaml
mode: normal
device_name_patterns: ["ai001", "ai002"]
log_level: verbose
dry_run: true
```

- Preview what would happen
- Check for errors
- Set `dry_run: false` when ready

---

### Workflow 4: Bulk Reinstall

Force update all devices (e.g., after YAML changes):

```yaml
mode: normal
update_when_version_matches: true
stop_on_upload_error: false
log_level: normal
```

- Updates all devices regardless of version
- Continues even if some fail
- Useful for applying configuration changes

---

## 📊 Monitoring

### Logs

**Live logs (Supervisor):**
- Add-on **Log** tab → real-time output (respects log_level setting)

**Persistent log (always full details):**
- `/config/esphome_smart_update.log`

**Progress file:**
- `/config/esphome_smart_update_progress.json`

### Example Output (Normal Mode)

```
======================================================================
ESPHome Selective Updates v2.0.12
======================================================================

NORMAL MODE - Smart Updates

======================================================================
Discovering Devices
======================================================================
Discovered 389 ESPHome devices

======================================================================
Filtering Devices
======================================================================
Total devices found: 389
Devices to process: 5
Devices skipped: 384

======================================================================
Processing Devices
======================================================================

[1/5] Processing: ai001
  → Compiling ai001.yaml...
  → Uploading to device...
  ✓ Successfully updated ai001

[2/5] Processing: ai002
  → Compiling ai002.yaml...
  → Uploading to device...
  ✓ Successfully updated ai002

...

======================================================================
Summary
======================================================================
Total devices: 389
Devices processed: 5
Devices failed: 0
Devices skipped: 384
```

### Example Output (Upload Only Mode)

```
======================================================================
ESPHome Selective Updates v2.0.12
======================================================================

UPLOAD ONLY MODE - Installing Pre-Compiled Binaries
Skipping compilation, using existing binaries

======================================================================
Processing Devices
======================================================================

[1/389] Uploading: ai001
  → Uploading to device (using existing binary)...
  ✓ Successfully uploaded ai001

[2/389] Uploading: ai002
  → Uploading to device (using existing binary)...
  ✓ Successfully uploaded ai002

...

======================================================================
Summary
======================================================================
Total devices: 389
Devices processed: 389
Devices failed: 0
```

---

## 🧠 How It Works

### Smart Update Logic

```python
for device in all_devices:
    # Read from /config/esphome/.esphome/storage/[device].yaml.json
    deployed_version = get_deployed_version(device)
    
    # Detected once at startup
    current_version = get_esphome_version()
    
    if deployed_version == current_version:
        skip(device)  # Already up-to-date
    else:
        update(device)  # Needs update
```

### Compilation Process

1. Uses `docker exec` to run ESPHome CLI inside the official ESPHome container
2. Compiles firmware: `esphome compile /config/esphome/<device>.yaml`
3. Binary saved to `/config/esphome/.esphome/build/<device>/firmware.bin`
4. Performs OTA upload via `esphome upload` command
5. Updates storage metadata in `/config/esphome/.esphome/storage/<device>.yaml.json`

### Resume Capability

Progress tracked in `/config/esphome_smart_update_progress.json`:

```json
{
  "done": ["ai001", "ai002", "ai003"],
  "failed": ["as007"],
  "skipped": []
}
```

If interrupted, the next run:
- Skips devices in "done" array
- Retries devices in "failed" array
- Re-evaluates devices in "skipped" array

---

## 🧰 Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `Docker socket not found` | Protection Mode is ON | Turn OFF Protection Mode in add-on Info tab |
| `ESPHome container not found` | Container name mismatch | Check `docker ps \| grep esphome` |
| All devices skipped | Already updated or wrong mode | Check storage files have metadata, verify mode setting |
| Devices skipped (no metadata) | Need repair mode | Run in repair mode first |
| Compilation failed | YAML syntax error | Check device YAML in ESPHome dashboard |
| Upload failed | Device offline or wrong password | Check device reachability and OTA password |
| Logs too verbose | Log level too high | Set `log_level: normal` or `quiet` |
| Can't troubleshoot | Log level too low | Check `/config/esphome_smart_update.log` |

### Finding Your ESPHome Container

```bash
docker ps | grep esphome
```

Common names:
- `addon_a0d7b954_esphome`
- `addon_15ef4d2f_esphome`
- `addon_5c53de3b_esphome`

### Viewing Storage Files

```bash
ls /config/esphome/.esphome/storage/
cat /config/esphome/.esphome/storage/ai001.yaml.json
```

Storage files contain:
- `esphome_version` - Deployed version
- `name` - Device name
- `address` - Device IP
- Build paths and metadata

---

## 🔧 Advanced Use Cases

### Update Only Specific Rooms

```yaml
mode: normal
device_name_patterns:
  - "living-room-*"
  - "bedroom-*"
  - "kitchen-*"
```

### Exclude Offline Devices

```yaml
mode: normal
skip_device_name_patterns:
  - "garage-*"
  - "basement-*"
  - "test-*"
```

### Batch Updates by Floor

```yaml
mode: normal
device_name_patterns:
  - "floor-1-*"
log_level: quiet
```

Run again with `floor-2-*`, `floor-3-*`, etc.

### Test Mode Before Production

```yaml
mode: normal
device_name_patterns: ["ai001", "ai002"]
log_level: verbose
dry_run: true
```

Review results, then:

```yaml
dry_run: false
device_name_patterns: []  # All devices
log_level: normal
```

---

## 📡 Home Assistant Integration

### Manual Button

```yaml
type: button
tap_action:
  action: call-service
  service: hassio.addon_start
  data:
    addon: local_esphome_selective_updates
name: Update ESPHome Devices
icon: mdi:chip
```

### Scheduled Nightly Update

```yaml
alias: ESPHome Nightly Update
trigger:
  - platform: time
    at: "02:00:00"
action:
  - service: hassio.addon_start
    data:
      addon: local_esphome_selective_updates
```

### Update with Notification

```yaml
alias: ESPHome Update with Notification
trigger:
  - platform: state
    entity_id: input_boolean.esphome_update_trigger
    to: "on"
action:
  - service: hassio.addon_start
    data:
      addon: local_esphome_selective_updates
  - wait_template: "{{ is_state('binary_sensor.esphome_selective_updates_running', 'off') }}"
    timeout: "02:00:00"
  - service: notify.mobile_app
    data:
      title: "ESPHome Updates"
      message: "Device updates completed. Check logs for details."
  - service: input_boolean.turn_off
    target:
      entity_id: input_boolean.esphome_update_trigger
```

---

## 📈 Performance

| Scenario | Time | Notes |
|----------|------|-------|
| **Normal mode (5 devices need update)** | ~10-15 min | Compile + upload only changed devices |
| **Normal mode (0 devices need update)** | ~30 sec | Discovery only, all skipped |
| **Repair mode (389 devices)** | ~2-3 hours | Compile-only, populate metadata |
| **Upload Only (389 devices)** | ~3-4 hours | OTA upload pre-compiled binaries |
| **Full workflow (Repair + Upload)** | ~5-7 hours | One-time setup for 389 devices |

**After initial setup:**
- Future updates: minutes instead of hours
- Only processes devices that actually changed
- 600x faster device discovery (1 sec vs 10-15 min)

---

## 🎁 Feature Request to ESPHome

I've submitted a feature request to make this functionality native to ESPHome Dashboard:

**https://github.com/orgs/esphome/discussions/3382**

If you'd like to see this become an official ESPHome feature, please 👍 the discussion and share your use case!

---

## 📝 Changelog Summary

| Version | Key Changes |
|---------|-------------|
| **2.0.12** | Mode selector dropdown, Upload Only mode, storage file path fixes, help text for all options |
| **2.0.11** | Storage file detection, metadata writing improvements |
| **2.0.6** | Repair mode for metadata rebuilding |
| **2.0.4** | ESPHome container auto-detection |
| **2.0.1** | Configurable log levels, reduced Supervisor log output |
| **2.0.0** | Major rewrite: dry run, safety checks, Protection Mode clarity |

See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

---

## 🧑‍💻 Support

### Self-Help

1. Check the add-on **Log** tab for errors
2. Inspect `/config/esphome_smart_update.log` for full details
3. Run with `log_level: verbose` or `log_level: debug` for diagnostics
4. Verify ESPHome container is running: `docker ps | grep esphome`
5. Confirm Protection Mode is OFF
6. Check storage files exist: `ls /config/esphome/.esphome/storage/`

### Getting Help

Open an issue on GitHub with:
- Add-on version (v2.0.12)
- ESPHome version
- Mode being used (Normal/Repair/Upload Only)
- Log excerpts from `/config/esphome_smart_update.log`
- Configuration (redact sensitive info)

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file

---

## 👨‍💻 Author

**Chris Judd** - Large-scale ESPHome management made reliable, repeatable, and readable.

Built to manage 389 ESPHome devices efficiently without drowning in logs.

---

## 🙏 Acknowledgments

- **ESPHome Team** - For creating an amazing firmware platform
- **Home Assistant Team** - For the add-on infrastructure
- **Community** - For testing, feedback, and feature requests

---

## 🔗 Links

- **Repository:** https://github.com/CSJudd/ha-addons-dev
- **ESPHome:** https://esphome.io
- **Home Assistant:** https://www.home-assistant.io
- **Issues:** https://github.com/CSJudd/ha-addons-dev/issues
- **Feature Request:** https://github.com/orgs/esphome/discussions/3382

---

**Quick Start:**

1. Install add-on
2. Turn OFF Protection Mode
3. Run **Repair mode** once (if metadata is missing)
4. Run **Upload Only mode** to install binaries
5. Use **Normal mode** for future updates

**That's it!** The add-on handles everything else automatically.