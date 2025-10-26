# ESPHome Smart Updater Add-on

Automatically update all ESPHome devices intelligently with resume capability for Home Assistant OS.

## Features

- **Smart Updates**: Only updates devices where `deployed_version ≠ current_version`
- **Offline Detection**: Pings devices before updating, skips offline devices
- **Resume Capability**: Tracks progress and can resume if interrupted
- **Comprehensive Logging**: All actions logged to `/config/esphome_smart_update.log`
- **Integration Ready**: Easily triggered by Home Assistant automations
- **Bulk Processing**: Handles 375+ devices efficiently

## Installation

### Step 1: Add the Repository

1. Navigate to **Supervisor** → **Add-on Store** → **⋮** (three dots menu, top right)
2. Select **Repositories**
3. Add this repository URL (or your local path):
   ```
   /addon
   ```
4. Click **Add** then **Close**

### Step 2: Install the Add-on

1. Refresh the add-on store page
2. Find **ESPHome Smart Updater** in the list
3. Click on it and press **Install**
4. Wait for installation to complete

### Step 3: Configure the Add-on

Click the **Configuration** tab and set:

```yaml
ota_password: "9c590ad5e0d08168b66b8ef48bd103e2"
skip_offline: true
delay_between_updates: 3
```

**Options explained:**
- `ota_password`: Your ESPHome OTA password (change if different)
- `skip_offline`: If `true`, skip devices that don't respond to ping
- `delay_between_updates`: Seconds to wait between device updates (1-60)

### Step 4: Start the Add-on

1. Go to the **Info** tab
2. **Disable** "Start on boot" (we'll trigger it via automation)
3. Click **Start** to test it manually

## Configuration

### Add-on Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `ota_password` | string | (your password) | ESPHome OTA password for all devices |
| `skip_offline` | boolean | `true` | Skip devices that don't respond to ping |
| `delay_between_updates` | integer | `3` | Seconds to wait between updates (1-60) |

## Usage

### Method 1: Manual Button

Create a script in Home Assistant:

1. Go to **Settings** → **Automations & Scenes** → **Scripts**
2. Click **+ Add Script** → **Create new script**
3. Name it: `ESPHome Update All`
4. Add this action:

```yaml
service: hassio.addon_start
data:
  addon: local_esphome_smart_updater
```

5. Save the script
6. Add a button to your dashboard:

```yaml
type: button
name: Update ESPHome Devices
icon: mdi:update
tap_action:
  action: call-service
  service: script.esphome_update_all
```

### Method 2: Scheduled Automation (9 PM Daily)

1. Go to **Settings** → **Automations & Scenes** → **Automations**
2. Click **+ Create Automation** → **Create new automation**
3. Name it: `ESPHome Nightly Update`
4. Add this configuration:

**Trigger:**
```yaml
platform: time
at: '21:00:00'
```

**Action:**
```yaml
service: hassio.addon_start
data:
  addon: local_esphome_smart_updater
```

5. Save the automation

### Method 3: Using Input Boolean Helper

If you have an existing `input_boolean.esphome_update_trigger`:

1. Create an automation:

**Trigger:**
```yaml
platform: state
entity_id: input_boolean.esphome_update_trigger
to: 'on'
```

**Actions:**
1. Start the add-on:
```yaml
service: hassio.addon_start
data:
  addon: local_esphome_smart_updater
```

2. Turn off the helper (after 5 seconds):
```yaml
delay:
  seconds: 5
```

```yaml
service: input_boolean.turn_off
target:
  entity_id: input_boolean.esphome_update_trigger
```

## Monitoring

### View Logs

1. In the add-on page, click the **Log** tab to see real-time progress
2. Or check the detailed log file at: `/config/esphome_smart_update.log`

### Check Progress

If the update is interrupted, progress is saved to:
```
/config/esphome_update_progress.json
```

This allows the add-on to resume and skip already-updated devices on the next run.

### Log Example

```
[2025-10-25 21:00:01] ================================================================================
[2025-10-25 21:00:01] ESPHome Smart Updater Add-on v1.0
[2025-10-25 21:00:01] ================================================================================
[2025-10-25 21:00:01] Found 375 total devices in ESPHome dashboard
[2025-10-25 21:00:02] 
[2025-10-25 21:00:02] [1/375] Processing: ai001
[2025-10-25 21:00:02]   Config: ai001.yaml
[2025-10-25 21:00:02]   Address: 10.128.47.1
[2025-10-25 21:00:02]   Deployed: 2025.9.1 | Current: 2025.10.2
[2025-10-25 21:00:02]   → Device has update: 2025.9.1 → 2025.10.2
[2025-10-25 21:00:02] Starting update for ai001
[2025-10-25 21:00:02]   → Compiling ai001.yaml in container
[2025-10-25 21:00:45]   → Compilation successful
[2025-10-25 21:00:45]   → Binary copied to /config/esphome/builds/ai001.bin
[2025-10-25 21:00:45]   → Uploading firmware to 10.128.47.1
[2025-10-25 21:01:23] ✓ Successfully updated ai001
```

## Network Requirements

This add-on requires access to:
- ESPHome Dashboard: `http://localhost:6052`
- Docker API: To execute compilation commands
- Your device network: For OTA updates via HTTP

## Device Types Supported

Works with all ESPHome device types including:
- Ratgdo Openers (GDR)
- Various outlet brands (Gosund, KMC, Sonoff)
- Switches and dimmers (MartinJerry, Athom, Kauf)
- Fan controllers
- Custom devices

## Troubleshooting

### Add-on won't start
- Check that ESPHome add-on is running
- Verify the OTA password is correct
- Check add-on logs for error messages

### Updates failing
- Ensure devices are online (check ping)
- Verify ESPHome container name is correct: `addon_15ef4d2f_esphome`
- Check network connectivity to devices
- Review detailed logs at `/config/esphome_smart_update.log`

### Progress file not clearing
- This is normal if some devices are offline or failed
- The progress file allows resuming interrupted updates
- Delete manually if needed: `/config/esphome_update_progress.json`

## Advanced Usage

### Custom ESPHome Container Name

If your ESPHome container has a different name, modify line 18 in `esphome_smart_updater.py`:

```python
CONTAINER_NAME = "your_container_name"
```

Then rebuild the add-on.

### Adjust Timeout

The default timeout per device is 300 seconds (5 minutes). To change:

Modify line 17 in `esphome_smart_updater.py`:
```python
TIMEOUT_PER_DEVICE = 600  # 10 minutes
```

## Support

For issues or questions:
1. Check the add-on logs
2. Review `/config/esphome_smart_update.log`
3. Check Home Assistant community forums

## Credits

Created for managing large-scale ESPHome deployments (375+ devices) with intelligent update logic and resume capability.

## License

MIT License
