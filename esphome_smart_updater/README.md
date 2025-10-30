# ESPHome Smart Updater Add-on

Automatically update all ESPHome devices intelligently with resume capability for **Home Assistant OS**.  
Now uses **Docker exec** to compile firmware safely inside the official ESPHome add-on container.

---

## 🚀 Features

- **Smart Updates** – Only updates devices where `deployed_version ≠ current_version`
- **Offline Detection** – Pings devices before updating, skips offline devices
- **Resume Capability** – Tracks progress and can resume if interrupted
- **Comprehensive Logging** – Logs to `/config/esphome_smart_update.log`
- **Integration Ready** – Trigger from Home Assistant automations or scripts
- **Bulk Processing** – Handles 375+ devices efficiently
- **Safe Compilation** – Builds inside the ESPHome add-on (no toolchain issues)
- **Graceful Stop** – Handles Supervisor stop signals, terminates safely, and preserves progress

---

## ⚙️ Requirements

- Home Assistant OS or Supervisor
- Official **ESPHome** add-on installed and running
- Supervisor Docker socket access (`docker_api: true`, `hassio_role: "manager"`)
- Correct ESPHome container name (default: `addon_15ef4d2f_esphome`)

---

## 🧩 Installation

### Step 1 — Add the Repository

1. Open **Settings → Add-ons → Add-on Store**
2. Click **⋮ → Repositories**
3. Add  
   `https://github.com/CSJudd/ha-addons-dev.git`
4. Click **Add**, then **Close**, then **Reload**

### Step 2 — Install the Add-on

1. Find **ESPHome Smart Updater**
2. Click **Install**
3. Wait for installation to complete

### Step 3 — Configure

```yaml
ota_password: "YOUR_ESPHOME_OTA_PASSWORD"
skip_offline: true
delay_between_updates: 3
esphome_container: "addon_15ef4d2f_esphome"
```

| Option | Type | Default | Description |
|--------|------|----------|-------------|
| `ota_password` | string | — | ESPHome OTA password |
| `skip_offline` | boolean | true | Skip devices that fail ping |
| `delay_between_updates` | int | 3 | Seconds between updates |
| `esphome_container` | string | addon_15ef4d2f_esphome | ESPHome container name |

### Step 4 — Start the Add-on

1. Go to the **Info** tab  
2. Turn **Start on boot** off (recommended)  
3. Click **Start**

Expected initial log lines:
```
[INFO] ESPHome Smart Updater starting (Docker exec mode)...
[INFO] Using Docker socket at: /run/docker.sock
```

---

## 🛠️ Usage

### Manual Button Script

```yaml
service: hassio.addon_start
data:
  addon: local_esphome_smart_updater
```

### Scheduled Nightly Update

```yaml
alias: ESPHome Nightly Update
trigger:
  - platform: time
    at: "21:00:00"
action:
  - service: hassio.addon_start
    data:
      addon: local_esphome_smart_updater
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
      addon: local_esphome_smart_updater
  - delay: 5
  - service: input_boolean.turn_off
    target:
      entity_id: input_boolean.esphome_update_trigger
```

---

## 📋 Monitoring

**Logs**
- Add-on **Log** tab → live output  
- Persistent file: `/config/esphome_smart_update.log`

**Progress File**
- `/config/esphome_update_progress.json` (used for resume after interruption)

**Example**
```
[2025-10-30 21:00:00] ESPHome Smart Updater v1.2.3 (Docker exec mode)
[2025-10-30 21:00:00] Found 375 devices
[2025-10-30 21:00:03] [1/375] Processing: ai001
[2025-10-30 21:00:03] → Compiling ai001.yaml in container addon_15ef4d2f_esphome
[2025-10-30 21:00:45] ✓ Successfully updated ai001
```

---

## 🧠 Internals

- Compiles via:  
  `docker exec <esphome_container> esphome compile /config/esphome/<device>.yaml`
- Copies resulting `.bin` to `/config/esphome/builds/`
- Performs OTA via HTTP POST to the device
- Catches SIGTERM/SIGINT and saves progress before exit

---

## 🧰 Troubleshooting

| Symptom | Likely Cause | Fix |
|--------|--------------|-----|
| `FATAL: No Docker socket mounted` | Supervisor didn’t mount socket | Ensure `"docker_api": true` and `"hassio_role": "manager"`, then reinstall |
| `xtensa-lx106-elf-g++ not found` | Old built-in compiler path used | Use version ≥ 1.2 (Docker exec mode). Reinstall if needed |
| Add-on not visible in Store | Bad JSON in any `config.json` or missing `repository.json` | Remove comments/trailing commas; add root `repository.json` |
| Repo listed but add-ons hidden | One invalid add-on file hides the repo | Check **Supervisor logs** for the exact file/line |
| Devices skipped | They were offline during run | Normal behavior |
| Progress file remains | Some failures pending | Delete `/config/esphome_update_progress.json` if desired |

---

## 📡 Network Requirements

- Access to ESPHome dashboard container (local Docker)
- Access to device IPs for HTTP OTA
- Supervisor Docker socket (`/run/docker.sock`)

---

## 🧾 Changelog Summary

| Version | Changes |
|--------|---------|
| **1.0.0** | Initial release (built-in compiler) |
| **1.1.x** | Graceful stop, resume; fixed CLI invocation |
| **1.2.0** | Switched to Docker exec mode (compile inside ESPHome) |
| **1.2.1** | Removed invalid `watchdog` boolean; JSON schema fixes |
| **1.2.3** | Require `hassio_role: "manager"` to ensure docker socket mount |

---

## 🧑‍💻 Support

1. Check the add-on **Log** tab  
2. Inspect `/config/esphome_smart_update.log`  
3. Verify `esphome_container` and device reachability  
4. Open an issue on the repository if the problem persists

---

**Author:** Chris Judd — Large-scale ESPHome management made reliable and repeatable.  
**License:** MIT
