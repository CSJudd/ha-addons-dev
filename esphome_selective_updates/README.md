# ESPHome Selective Updates

**Smart bulk updates for ESPHome devices - only updates devices that actually need it**

---

## 🎯 Why This Add-on Exists

### The Problem

ESPHome's built-in "Update All" button has a critical flaw:

- ❌ **No intelligence** - Recompiles ALL devices, even ones already updated
- ❌ **No resume** - If interrupted at device #200, starts over from #1
- ❌ **Wastes time** - Takes 10+ hours for 375 devices when only 5 need updates
- ❌ **No offline detection** - Tries to update unreachable devices and fails
- ❌ **Floods logs** - Thousands of log lines make troubleshooting impossible

### The Solution

This add-on fixes ESPHome's missing functionality:

- ✅ **Smart updates** - Only compiles devices where `deployed_version ≠ current_version`
- ✅ **Resume capability** - Picks up exactly where it left off if interrupted
- ✅ **Offline detection** - Pings devices first, skips unreachable ones
- ✅ **Progress tracking** - Detailed logging and state persistence
- ✅ **Efficiency** - 15 minutes instead of 10 hours for large deployments
- ✅ **Manageable logs** - Configurable log levels keep Supervisor logs clean

**Real-world results:** Updates 375 devices in ~30 minutes instead of 10+ hours, with logs you can actually read.

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

**Note:** This is a documented limitation until ESPHome adds a native compile API (which we're requesting - see below).

---

## 🚀 Features

- **Smart Updates** – Only updates devices where deployed_version ≠ current_version
- **Configurable Logging** – Control log verbosity (quiet/normal/verbose/debug)
- **Offline Detection** – Pings devices before updating, skips offline devices
- **Resume Capability** – Tracks progress, can resume if interrupted
- **Dry Run Mode** – Preview what would be updated without actually updating
- **Batch Control** – Limit updates per run, whitelist specific devices
- **Comprehensive Logging** – Logs to `/config/esphome_smart_update.log` with full details
- **Clean Supervisor Logs** – Manageable output in Home Assistant Logs tab
- **Integration Ready** – Trigger from Home Assistant automations or scripts
- **Bulk Processing** – Efficiently handles 375+ devices
- **Safe Compilation** – Builds inside the ESPHome add-on (no toolchain issues)
- **Graceful Stop** – Handles Supervisor stop signals, preserves progress

---

## 📋 Requirements

- Home Assistant OS or Supervisor
- Official **ESPHome** add-on installed and running
- Supervisor Docker socket access (`docker_api: true`, `hassio_role: "manager"`)
- **Protection Mode OFF** (see above)
- Correct ESPHome container name (default: `addon_5c53de3b_esphome`)

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

#### Basic Configuration

```yaml
device_name_patterns: []           # Optional: filter by device name (e.g., ["living-*", "bedroom-*"])
skip_device_name_patterns: []      # Optional: exclude by device name
update_when_no_deployed_version: false
update_when_version_matches: false
log_level: "normal"                # New in 2.0.1: quiet|normal|verbose|debug
```

#### Advanced Options

```yaml
# Testing & Control
dry_run: false                    # Preview updates without executing
yaml_name_patterns: []            # Filter by YAML filename
skip_yaml_name_patterns: []       # Exclude by YAML filename

# Housekeeping
clear_log_on_start: false         # Clear log every start
clear_log_on_version_change: true # Clear log when add-on updates
clear_log_now: false              # One-time log clear trigger
clear_progress_on_start: false    # Clear progress every start
clear_progress_now: false         # One-time progress clear trigger

# Error Handling
stop_on_compilation_warning: false
stop_on_compilation_error: true
stop_on_upload_error: true
```

#### Configuration Reference

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `device_name_patterns` | list | [] | Include only devices matching these patterns (supports `*` wildcard) |
| `skip_device_name_patterns` | list | [] | Exclude devices matching these patterns |
| `yaml_name_patterns` | list | [] | Include only YAML files matching these patterns |
| `skip_yaml_name_patterns` | list | [] | Exclude YAML files matching these patterns |
| `update_when_no_deployed_version` | boolean | false | Update devices with no deployed version |
| `update_when_version_matches` | boolean | false | Update even when versions match |
| `log_level` | list | normal | Output verbosity: quiet\|normal\|verbose\|debug |
| `dry_run` | boolean | false | Preview mode (no actual updates) |
| `clear_log_on_start` | boolean | false | Clear log file on every start |
| `clear_log_on_version_change` | boolean | true | Clear log when add-on version changes |
| `clear_log_now` | boolean | false | One-time trigger to clear log |
| `clear_progress_on_start` | boolean | false | Clear progress on every start |
| `clear_progress_now` | boolean | false | One-time trigger to clear progress |
| `stop_on_compilation_warning` | boolean | false | Stop if compilation produces warnings |
| `stop_on_compilation_error` | boolean | true | Stop if compilation fails |
| `stop_on_upload_error` | boolean | true | Stop if upload fails |

### Step 4 – Disable Protection Mode

**CRITICAL:** You must turn OFF Protection Mode or the add-on will not work.

1. Go to the **Info** tab
2. Find **"Protection mode"** toggle
3. Turn it **OFF**
4. Read the safety explanation above if you have concerns

### Step 5 – Choose Your Log Level

**New in 2.0.1:** Control how much output appears in the Supervisor Logs tab.

| Level | Output | Best For |
|-------|--------|----------|
| **quiet** | Bare minimum (~50 lines for 377 devices) | Daily automated runs, large deployments |
| **normal** | Standard operation (~200 lines) | General use, manual runs |
| **verbose** | Detailed info (~1000 lines) | First-time setup, understanding behavior |
| **debug** | Everything (thousands of lines) | Troubleshooting specific issues |

**Important:** The persistent log file (`/config/esphome_smart_update.log`) always contains full logs regardless of this setting, so you can troubleshoot later without re-running.

**Recommendation:** Start with `verbose` for your first run to understand what's happening, then switch to `normal` or `quiet` for regular use.

### Step 6 – Start the Add-on

1. Go to the **Info** tab
2. Turn **Start on boot** OFF (recommended - run on-demand)
3. Click **Start**

Expected initial log lines (normal mode):
```
======================================================================
ESPHome Selective Updates v2.0.1
======================================================================
Log level: normal

======================================================================
Discovering Devices
======================================================================
Discovered 377 ESPHome devices
```

---

## 🛠️ Usage

### Manual Button Script

Create a button in Home Assistant:

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

### Input Boolean Trigger

```yaml
trigger:
  - platform: state
    entity_id: input_boolean.esphome_update_trigger
    to: "on"
action:
  - service: hassio.addon_start
    data:
      addon: local_esphome_selective_updates
  - delay: 5
  - service: input_boolean.turn_off
    target:
      entity_id: input_boolean.esphome_update_trigger
```

### Dry Run First (Recommended)

Before your first real run:

1. Set `dry_run: true` in options
2. Set `log_level: verbose` to see details
3. Start the add-on
4. Review logs to see what would be updated
5. Set `dry_run: false` and `log_level: normal` when satisfied
6. Run for real

---

## 📊 Monitoring

### Logs

**Live logs (Supervisor):**
- Add-on **Log** tab → real-time output (respects log_level setting)

**Persistent log (always full details):**
- `/config/esphome_smart_update.log`

**Progress file:**
- `/config/esphome_update_progress.json`

### Example Output (Normal Level)

```
======================================================================
ESPHome Selective Updates v2.0.1
======================================================================
Log level: normal

======================================================================
Discovering Devices
======================================================================
Discovered 377 ESPHome devices

======================================================================
Filtering Devices
======================================================================
Total devices found: 377
Devices to process: 5
Devices skipped: 372

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

[3/5] Processing: as007
  → Compiling as007.yaml...
  ✗ Upload failed: Connection refused (device offline or wrong IP?)

[4/5] Processing: br005
  → Compiling br005.yaml...
  → Uploading to device...
  ✓ Successfully updated br005

[5/5] Processing: lr012
  → Compiling lr012.yaml...
  → Uploading to device...
  ✓ Successfully updated lr012

======================================================================
Summary
======================================================================
Total devices: 377
Devices processed: 4
Devices failed: 1
Devices skipped: 372

Failed devices:
  - as007

Log file: /config/esphome_smart_update.log
Progress file: /config/esphome_update_progress.json
```

### Example Output (Quiet Level)

```
======================================================================
ESPHome Selective Updates v2.0.1
======================================================================

======================================================================
Discovering Devices
======================================================================

======================================================================
Filtering Devices
======================================================================

======================================================================
Processing Devices
======================================================================

======================================================================
Summary
======================================================================
Total devices: 377
Devices processed: 4
Devices failed: 1
Devices skipped: 372

Failed devices:
  - as007

Log file: /config/esphome_smart_update.log
Progress file: /config/esphome_update_progress.json
```

### Clearing Massive Supervisor Logs

If you already have huge logs from previous runs:

```bash
# SSH into Home Assistant
ha addons stop local_esphome_selective_updates
ha supervisor logs clear
# or: journalctl --vacuum-time=1s
ha addons start local_esphome_selective_updates
```

---

## 🧠 How It Works

### Compilation Process

1. Uses `docker exec` to run ESPHome CLI inside the official ESPHome add-on
2. Compiles firmware: `esphome compile /config/esphome/<device>.yaml`
3. Locates compiled `.bin` file in container
4. Copies binary to `/config/esphome/builds/` on host
5. Performs OTA upload via `esphome upload` command

### Smart Update Logic

```python
for device in all_devices:
    deployed_version = get_deployed_version(device)  # From .storage file
    current_version  = get_current_version(device)   # From esphome version command
    
    if deployed_version == current_version:
        skip(device)  # Already up-to-date
    else:
        update(device)  # Needs update
```

### Resume Capability

Progress is tracked in `/config/esphome_update_progress.json`:

```json
{
  "done": ["ai001", "ai002", "ai003"],
  "failed": ["as007"],
  "skipped": []
}
```

If the add-on is stopped or crashes, the next run will:
- Skip devices in "done" array
- Retry devices in "failed" array (in case they're back online)
- Re-evaluate devices in "skipped" array

### Log Level System

**New in 2.0.1:** All logging goes through a level filter.

```python
log_quiet()   # Always shown: headers, errors, summary
log_normal()  # Standard: device processing messages
log_verbose() # Detailed: version info, skip reasons
log_debug()   # Everything: command outputs, compilation logs
```

- **Supervisor logs** respect the configured level
- **Persistent log file** always gets ALL logs for troubleshooting

---

## 🧰 Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `FATAL: Docker socket not found` | Protection Mode is ON | Turn OFF Protection Mode in add-on Info tab |
| `ESPHome container not found` | Container name incorrect | Check actual name with `docker ps`, update config |
| `Cannot communicate with Docker` | Protection Mode or socket issue | Ensure Protection Mode is OFF, restart add-on |
| Devices skipped | Already updated, offline, or filtered | Check logs for skip reasons (use `log_level: verbose`) |
| Compilation failed | YAML syntax error or missing dependencies | Check device YAML in ESPHome dashboard |
| OTA upload failed | Device offline, wrong password, or network issue | Check device reachability and OTA password |
| Logs too verbose | Log level set too high | Set `log_level: normal` or `log_level: quiet` |
| Can't troubleshoot | Log level too low | Check `/config/esphome_smart_update.log` for full details |

### Common ESPHome Container Names

If `addon_5c53de3b_esphome` doesn't work, try:
- `addon_15ef4d2f_esphome`
- `addon_a0d7b954_esphome`

To find your actual container name:
```bash
docker ps | grep esphome
```

Or check **Settings → System → Logs → Supervisor** for "Starting addon_XXXXXXXX_esphome"

### Viewing Progress File

```bash
cat /config/esphome_update_progress.json
```

To manually reset progress:
```yaml
clear_progress_now: true
```
(Remember to set it back to `false` after)

### Viewing Full Logs

Even with `log_level: quiet`, full logs are always available:

```bash
tail -f /config/esphome_smart_update.log
```

Or download via **File Editor** add-on or Samba share.

---

## 🔧 Advanced Use Cases

### Update Only Specific Devices

```yaml
device_name_patterns:
  - "living-room-*"
  - "bedroom-*"
  - "kitchen-sensor"
```

### Exclude Problematic Devices

```yaml
skip_device_name_patterns:
  - "garage-*"        # Offline devices
  - "test-*"          # Test devices
```

### Batch Updates with Minimal Logs

```yaml
log_level: "quiet"
device_name_patterns:
  - "floor-1-*"
```

Run again with `floor-2-*`, `floor-3-*`, etc.

### Verbose Testing Then Quiet Production

**First run:**
```yaml
dry_run: true
log_level: verbose
```

**After verification:**
```yaml
dry_run: false
log_level: quiet
```

### Nightly Updates with Notification

```yaml
alias: ESPHome Nightly Update with Notification
trigger:
  - platform: time
    at: "02:00:00"
action:
  - service: hassio.addon_start
    data:
      addon: local_esphome_selective_updates
  - delay: 300  # Wait 5 minutes for completion
  - service: persistent_notification.create
    data:
      title: "ESPHome Updates"
      message: "Nightly device updates completed. Check /config/esphome_smart_update.log for details."
```

---

## 📡 Network Requirements

- Access to ESPHome dashboard container (local Docker)
- Access to device IPs for HTTP OTA (ports 3232, 8266, or 6053)
- Supervisor Docker socket (`/run/docker.sock`)

---

## 🎁 Feature Request to ESPHome

I've submitted a feature request to make this functionality native to ESPHome Dashboard:

**https://github.com/orgs/esphome/discussions/3382**

If you'd like to see this become an official ESPHome feature, please 👍 the discussion and share your use case!

Until then, this add-on provides the functionality you need today. If ESPHome adds a compile API, I'll refactor this add-on to use it and make Protection Mode unnecessary.

---

## 🧾 Changelog Summary

| Version | Key Changes |
|---------|-------------|
| **2.0.1** | Added configurable log levels (quiet/normal/verbose/debug), fixed log clearing, drastically reduced Supervisor log output |
| **2.0.0** | Major rewrite: Added dry run, offline detection, batch control, better safety checks, clearer Protection Mode messaging |
| **1.2.x** | Switched to Docker exec mode, added graceful stop |
| **1.1.x** | Added resume capability with progress tracking |
| **1.0.0** | Initial release with smart version-based updates |

See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

---

## 🧑‍💻 Support

### Self-Help

1. Check the add-on **Log** tab for errors
2. Inspect `/config/esphome_smart_update.log` for detailed history (always has full logs)
3. Try running with `log_level: verbose` or `log_level: debug` for more details
4. Verify ESPHome container name is correct (`docker ps | grep esphome`)
5. Confirm Protection Mode is OFF
6. Test device reachability with manual ping

### Getting Help

If you encounter issues:

1. **Enable verbose/debug mode** and check logs
2. **Check ESPHome add-on is running** (`docker ps | grep esphome`)
3. **Open an issue** on GitHub with:
   - Add-on version
   - ESPHome version
   - Log level used
   - Relevant log excerpts from `/config/esphome_smart_update.log`
   - Configuration (redact passwords)

### Feature Requests

Have an idea? Open an issue with:
- Clear description of the problem
- Proposed solution
- Your use case

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file

---

## 👨‍💻 Author

**Chris Judd** - Large-scale ESPHome management made reliable, repeatable, and readable.

Built out of necessity to manage 375+ ESPHome devices efficiently without drowning in logs.

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

**Remember:** This add-on is a power-user tool that fixes real limitations in ESPHome. Use it responsibly, understand the Protection Mode requirement, and help advocate for native ESPHome support for this functionality.

**Tip:** Start with `log_level: verbose` to understand how it works, then switch to `normal` or `quiet` for daily use. Full logs are always available in `/config/esphome_smart_update.log` when you need them.