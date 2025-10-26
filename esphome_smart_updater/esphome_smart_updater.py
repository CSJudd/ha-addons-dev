#!/usr/bin/env python3
"""
ESPHome Smart Updater Add-on
Automatically updates ESPHome devices intelligently with resume capability
"""

import os
import json
import time
import asyncio
import requests
from datetime import datetime
import subprocess
import sys

# Configuration from add-on options
OPTIONS_FILE = "/data/options.json"
ESPHOME_URL = "http://localhost:6052"
LOG_FILE = "/config/esphome_smart_update.log"
PROGRESS_FILE = "/config/esphome_update_progress.json"
TIMEOUT_PER_DEVICE = 300
CONTAINER_NAME = "addon_15ef4d2f_esphome"

def load_options():
    """Load add-on options from Home Assistant"""
    try:
        with open(OPTIONS_FILE, 'r') as f:
            options = json.load(f)
        return options
    except Exception as e:
        print(f"Error loading options: {e}")
        return {}

def log_message(message):
    """Log messages to both console and log file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry, flush=True)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(log_entry + '\n')
    except Exception as e:
        print(f"Error writing to log file: {e}", flush=True)

def get_esphome_devices():
    """Fetch all configured ESPHome devices from the dashboard"""
    try:
        response = requests.get(f"{ESPHOME_URL}/devices", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('configured', [])
        else:
            log_message(f"Failed to get devices: HTTP {response.status_code}")
        return []
    except Exception as e:
        log_message(f"Error getting devices: {e}")
        return []

def check_device_needs_update(device):
    """Check if device's deployed version differs from current version"""
    try:
        deployed = device.get('deployed_version', '')
        current = device.get('current_version', '')
        
        if not deployed or not current:
            return False
            
        needs_update = deployed != current
        
        if needs_update:
            log_message(f"  → Device has update: {deployed} → {current}")
        
        return needs_update
    except Exception as e:
        log_message(f"Error checking update status: {e}")
        return False

def ping_device(address):
    """Check if device is online via ping"""
    try:
        response = os.system(f"ping -c 1 -W 2 {address} > /dev/null 2>&1")
        return response == 0
    except:
        return False

async def update_device_http(device_name, device_config, device_address, ota_password):
    """
    Update a single ESPHome device via HTTP OTA
    
    Process:
    1. Compile firmware inside ESPHome container
    2. Copy binary to builds directory
    3. Upload via HTTP OTA to device
    """
    log_message(f"Starting update for {device_name}")
    
    # Paths for binary files
    bin_path = f"/config/esphome/builds/{os.path.basename(device_config).replace('.yaml', '.bin')}"
    source_path = f"/config/esphome/.esphome/build/{device_name}/.pioenvs/{device_name}/firmware.bin"
    
    try:
        # Step 1: Compile firmware inside ESPHome container
        log_message(f"  → Compiling {device_config} in container")
        compile_cmd = f"docker exec {CONTAINER_NAME} esphome compile /config/esphome/{device_config}"
        
        result = subprocess.run(
            compile_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_PER_DEVICE
        )
        
        if result.returncode != 0:
            log_message(f"✗ Compilation failed for {device_name}")
            log_message(f"  Error: {result.stderr[:500]}")
            return False, "compile_failed"
        
        log_message(f"  → Compilation successful")
        
        # Step 2: Copy binary to builds directory
        if os.path.exists(source_path):
            os.makedirs(os.path.dirname(bin_path), exist_ok=True)
            os.system(f"cp {source_path} {bin_path}")
            
            if not os.path.exists(bin_path):
                log_message(f"✗ Failed to copy binary from {source_path} to {bin_path}")
                return False, "copy_failed"
            
            log_message(f"  → Binary copied to {bin_path}")
        else:
            log_message(f"✗ Binary not found at {source_path}")
            return False, "compile_failed"

        # Step 3: Upload via HTTP OTA
        log_message(f"  → Uploading firmware to {device_address}")
        
        with open(bin_path, 'rb') as f:
            response = requests.post(
                f"http://{device_address}/update",
                files={"file": f},
                data={"password": ota_password},
                timeout=TIMEOUT_PER_DEVICE
            )
        
        if response.status_code == 200:
            log_message(f"✓ Successfully updated {device_name}")
            return True, "success"
        else:
            log_message(f"✗ OTA upload failed with status {response.status_code}")
            if response.text:
                log_message(f"  Response: {response.text[:200]}")
            return False, f"ota_failed_{response.status_code}"
            
    except subprocess.TimeoutExpired:
        log_message(f"✗ Compilation timeout for {device_name}")
        return False, "compile_timeout"
    except subprocess.CalledProcessError as e:
        log_message(f"✗ Compilation failed: {e}")
        return False, "compile_failed"
    except requests.Timeout:
        log_message(f"✗ OTA upload timeout for {device_name}")
        return False, "ota_timeout"
    except Exception as e:
        log_message(f"✗ Error updating {device_name}: {str(e)}")
        return False, str(e)

def load_progress():
    """Load progress file to resume interrupted updates"""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            log_message(f"Error loading progress file: {e}")
            return {}
    return {}

def save_progress(progress):
    """Save progress to file for resume capability"""
    try:
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(progress, f, indent=2)
    except Exception as e:
        log_message(f"Error saving progress file: {e}")

async def main():
    """Main update process"""
    log_message("=" * 80)
    log_message("ESPHome Smart Updater Add-on v1.0")
    log_message("=" * 80)
    
    # Load options
    options = load_options()
    ota_password = options.get('ota_password', '9c590ad5e0d08168b66b8ef48bd103e2')
    skip_offline = options.get('skip_offline', True)
    delay_between_updates = options.get('delay_between_updates', 3)
    
    log_message(f"Options: skip_offline={skip_offline}, delay={delay_between_updates}s")
    
    # Load existing progress
    progress = load_progress()
    if progress:
        log_message(f"Resuming from previous run ({len(progress)} devices tracked)")
    
    # Get all devices
    devices = get_esphome_devices()
    
    if not devices:
        log_message("No devices found or error connecting to ESPHome")
        log_message("Make sure ESPHome add-on is running at http://localhost:6052")
        return
    
    log_message(f"Found {len(devices)} total devices in ESPHome dashboard")
    
    # Statistics tracking
    stats = {
        'total': len(devices),
        'updated': 0,
        'skipped': 0,
        'no_update_needed': 0,
        'failed': 0,
        'offline': 0
    }
    
    # Process each device
    for idx, device in enumerate(devices, 1):
        device_name = device.get('name', 'unknown')
        device_config = os.path.basename(device.get('configuration', f"{device_name}.yaml"))
        device_address = device.get('address', '')
        deployed_version = device.get('deployed_version', 'unknown')
        current_version = device.get('current_version', 'unknown')
        
        log_message("")
        log_message(f"[{idx}/{len(devices)}] Processing: {device_name}")
        log_message(f"  Config: {device_config}")
        log_message(f"  Address: {device_address}")
        log_message(f"  Deployed: {deployed_version} | Current: {current_version}")
        
        # Check if already successfully updated
        if progress.get(device_name, {}).get('status') == 'success':
            log_message(f"⊘ Skipping {device_name} (already updated in this run)")
            stats['skipped'] += 1
            continue
        
        # Check if update is needed
        if not check_device_needs_update(device):
            log_message(f"✓ No update needed for {device_name}")
            stats['no_update_needed'] += 1
            continue
        
        # Check if device is online
        if device_address:
            if not ping_device(device_address):
                log_message(f"⊗ Device {device_name} ({device_address}) is offline")
                stats['offline'] += 1
                progress[device_name] = {
                    'status': 'offline',
                    'timestamp': datetime.now().isoformat(),
                    'deployed_version': deployed_version,
                    'target_version': current_version
                }
                save_progress(progress)
                
                if skip_offline:
                    log_message(f"  → Skipping offline device")
                    continue
        else:
            log_message(f"⚠ No address found for {device_name}, attempting update anyway")
        
        # Perform update
        success, message = await update_device_http(
            device_name,
            device_config,
            device_address,
            ota_password
        )
        
        # Update statistics and progress
        if success:
            stats['updated'] += 1
            progress[device_name] = {
                'status': 'success',
                'timestamp': datetime.now().isoformat(),
                'deployed_version': deployed_version,
                'updated_to_version': current_version
            }
        else:
            stats['failed'] += 1
            progress[device_name] = {
                'status': 'failed',
                'timestamp': datetime.now().isoformat(),
                'error': message,
                'deployed_version': deployed_version,
                'target_version': current_version
            }
        
        save_progress(progress)
        
        # Delay between updates
        if idx < len(devices):
            await asyncio.sleep(delay_between_updates)
    
    # Final summary
    log_message("")
    log_message("=" * 80)
    log_message("Update Process Complete")
    log_message("=" * 80)
    for key, value in stats.items():
        label = key.replace('_', ' ').title()
        log_message(f"{label:.<30} {value}")
    log_message("=" * 80)
    
    # Clean up progress file if everything succeeded
    if stats['failed'] == 0 and stats['offline'] == 0:
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)
            log_message("✓ Progress file cleaned up (all devices updated successfully)")
    else:
        log_message(f"⚠ Progress file retained for resume capability")
        log_message(f"  Location: {PROGRESS_FILE}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
        sys.exit(0)
    except KeyboardInterrupt:
        log_message("Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        log_message(f"Fatal error: {e}")
        sys.exit(1)
