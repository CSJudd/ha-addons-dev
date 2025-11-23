#!/usr/bin/env python3
"""
ESPHome Selective Updates Add-on
Intelligently updates ESPHome devices based on version changes
"""

import sys
import os
import json
import subprocess
import time
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

# ============================================================================
# PATHS & CONSTANTS
# ============================================================================

CONFIG_DIR = Path("/config")
ESPHOME_DIR = CONFIG_DIR / "esphome"
DASHBOARD_FILE = ESPHOME_DIR / ".esphome" / "dashboard.json"
STATE_FILE = CONFIG_DIR / "esphome_smart_update_state.json"
PROGRESS_FILE = CONFIG_DIR / "esphome_smart_update_progress.json"
LOG_FILE = CONFIG_DIR / "esphome_smart_update.log"

DEFAULTS = {
    "device_name_patterns": [],
    "skip_device_name_patterns": [],
    "yaml_name_patterns": [],
    "skip_yaml_name_patterns": [],
    "update_when_no_deployed_version": False,
    "update_when_version_matches": False,
    "clear_progress_on_start": False,
    "clear_progress_now": False,
    "clear_log_on_start": False,
    "clear_log_on_version_change": True,
    "clear_log_now": False,
    "stop_on_compilation_warning": False,
    "stop_on_compilation_error": True,
    "stop_on_upload_error": True,
    "dry_run": False,
    "log_level": "normal",
    "repair_dashboard_metadata": False,
    "repair_skip_existing_metadata": True,
    "debug_test_single_device": "",  # Set to device name to test just one device
}

# Log level mapping
LOG_LEVEL_MAP = {
    "quiet": 0,
    "normal": 1,
    "verbose": 2,
    "debug": 3
}
CURRENT_LOG_LEVEL = 1  # Default to normal

# ============================================================================
# LOGGING UTILITIES
# ============================================================================

def ts() -> str:
    """Generate timestamp for logging"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

def set_log_level(level: str):
    """Set the current log level"""
    global CURRENT_LOG_LEVEL
    CURRENT_LOG_LEVEL = LOG_LEVEL_MAP.get(level.lower(), 1)

def should_log(level: str = "normal") -> bool:
    """Check if message should be logged at current level"""
    msg_level = LOG_LEVEL_MAP.get(level.lower(), 1)
    return msg_level <= CURRENT_LOG_LEVEL

def log(msg: str, level: str = "normal"):
    """Log message to both stdout and file"""
    line = f"{ts()} {msg}"
    
    # Always log to file (full history)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    
    # Only log to stdout if level permits
    if should_log(level):
        print(line, flush=True)

def log_quiet(msg: str):
    """Log message at quiet level (always shown)"""
    log(msg, level="quiet")

def log_normal(msg: str):
    """Log message at normal level"""
    log(msg, level="normal")

def log_verbose(msg: str):
    """Log message at verbose level"""
    log(msg, level="verbose")

def log_debug(msg: str):
    """Log message at debug level"""
    log(msg, level="debug")

def log_header(msg: str):
    """Log a section header (always shown)"""
    log_quiet("")
    log_quiet("=" * 70)
    log_quiet(msg)
    log_quiet("=" * 70)

def truncate_file(path: Path) -> bool:
    """
    Clear a file's contents
    Returns: True if successful, False otherwise
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            pass
        return True
    except Exception as e:
        print(f"ERROR: Failed to truncate {path}: {e}", file=sys.stderr)
        return False

# ============================================================================
# CONFIGURATION & STATE MANAGEMENT
# ============================================================================

def load_options() -> Dict:
    """Load add-on configuration from /data/options.json"""
    options_path = Path("/data/options.json")
    try:
        with options_path.open("r", encoding="utf-8") as f:
            opts = json.load(f)
        # Merge with defaults
        result = DEFAULTS.copy()
        result.update(opts)
        return result
    except Exception as e:
        log_quiet(f"Warning: failed to load options: {e}")
        return DEFAULTS.copy()

def load_state() -> Dict:
    """Load persistent state"""
    if not STATE_FILE.exists():
        return {}
    try:
        with STATE_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_state(state: Dict):
    """Save persistent state"""
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with STATE_FILE.open("w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        log_quiet(f"Warning: failed to save state: {e}")

def load_progress() -> Dict:
    """Load progress tracking"""
    if not PROGRESS_FILE.exists():
        return {"done": [], "failed": [], "skipped": []}
    try:
        with PROGRESS_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"done": [], "failed": [], "skipped": []}

def save_progress(progress: Dict):
    """Save progress tracking"""
    try:
        PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with PROGRESS_FILE.open("w", encoding="utf-8") as f:
            json.dump(progress, f, indent=2)
    except Exception as e:
        log_quiet(f"Warning: failed to save progress: {e}")

def perform_housekeeping(opts: Dict, state: Dict, progress: Dict) -> Dict:
    """Handle log and progress file cleanup"""
    addon_version = os.environ.get("ADDON_VERSION", "unknown")
    
    # Version change detection
    if opts.get("clear_log_on_version_change", True):
        if addon_version and addon_version != state.get("last_version"):
            if truncate_file(LOG_FILE):
                log_normal(f"Add-on version changed: {state.get('last_version')} → {addon_version}")
                log_normal("Log file cleared due to version change")
            state["last_version"] = addon_version
            save_state(state)
    
    # Log clearing confirmation (run.sh handles the actual clearing)
    if opts.get("clear_log_on_start", False):
        log_verbose("Log file was cleared on start")
    
    # Clear log now (one-time trigger)
    if bool(opts.get("clear_log_now", False)) and not state.get("clear_log_now_consumed", False):
        log_normal("Log file was cleared (clear_log_now trigger)")
        state["clear_log_now_consumed"] = True
        save_state(state)
    elif not bool(opts.get("clear_log_now", False)) and state.get("clear_log_now_consumed", False):
        state["clear_log_now_consumed"] = False
        save_state(state)
    
    # Progress clearing
    if opts.get("clear_progress_on_start", False):
        if truncate_file(PROGRESS_FILE):
            progress = {"done": [], "failed": [], "skipped": []}
            save_progress(progress)
            log_normal("Progress file cleared (clear_progress_on_start)")
    
    if bool(opts.get("clear_progress_now", False)) and not state.get("clear_progress_now_consumed", False):
        if truncate_file(PROGRESS_FILE):
            progress = {"done": [], "failed": [], "skipped": []}
            save_progress(progress)
            log_normal("Progress file cleared (clear_progress_now trigger)")
        state["clear_progress_now_consumed"] = True
        save_state(state)
    elif not bool(opts.get("clear_progress_now", False)) and state.get("clear_progress_now_consumed", False):
        state["clear_progress_now_consumed"] = False
        save_state(state)
    
    return progress

# ============================================================================
# SAFETY CHECKS
# ============================================================================

def verify_safe_operation() -> bool:
    """Verify the add-on can operate safely"""
    if not ESPHOME_DIR.exists():
        log_quiet(f"ERROR: ESPHome directory not found: {ESPHOME_DIR}")
        return False
    
    yaml_files = list(ESPHOME_DIR.glob("*.yaml"))
    if not yaml_files:
        log_quiet(f"ERROR: No .yaml files found in {ESPHOME_DIR}")
        return False
    
    log_debug(f"Found {len(yaml_files)} YAML files in {ESPHOME_DIR}")
    return True

# ============================================================================
# DASHBOARD.JSON INTERACTION
# ============================================================================

def read_dashboard_json() -> Dict:
    """Read the ESPHome dashboard.json file"""
    if not DASHBOARD_FILE.exists():
        log_debug(f"Dashboard file not found: {DASHBOARD_FILE}")
        return {}
    
    try:
        with DASHBOARD_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        log_debug(f"Error reading dashboard.json: {e}")
        return {}

def get_dashboard_versions(device_name: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Get deployed_version and current_version from dashboard.json
    Returns: (deployed_version, current_version)
    """
    dashboard = read_dashboard_json()
    
    for device in dashboard.get("devices", []):
        if device.get("name") == device_name:
            deployed = device.get("deployed_version")
            current = device.get("current_version")
            return (deployed, current)
    
    return (None, None)

# ============================================================================
# ESPHOME INTERACTION/COMPILATION
# ============================================================================

def run_esphome_command(args: List[str], cwd: Optional[Path] = None) -> Tuple[int, str, str]:
    """
    Execute an ESPHome command via docker exec
    Returns: (returncode, stdout, stderr)
    """
    # Get ESPHome container name from environment (set by run.sh)
    esphome_container = os.environ.get("ESPHOME_CONTAINER", "")
    
    if not esphome_container:
        error_msg = "ESPHOME_CONTAINER environment variable not set"
        log_debug(error_msg)
        return (1, "", error_msg)
    
    # Build the docker exec command
    cmd = [
        "docker", "exec", "-i",
        esphome_container,
        "esphome"
    ] + args
    
    log_debug(f"Running command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=1800  # 30 minute timeout
        )
        
        # If we get "page not found", it's likely a Docker API error
        if "page not found" in result.stderr.lower() or "page not found" in result.stdout.lower():
            log_debug(f"Docker error - container may not exist: {esphome_container}")
            log_debug(f"Stderr: {result.stderr}")
            log_debug(f"Stdout: {result.stdout}")
        
        return (result.returncode, result.stdout, result.stderr)
    except subprocess.TimeoutExpired:
        return (124, "", "Command timed out after 30 minutes")
    except FileNotFoundError:
        return (1, "", "Docker command not found - is Docker installed?")
    except Exception as e:
        return (1, "", str(e))

def get_esphome_devices() -> List[Dict]:
    """
    Get list of ESPHome devices and their current versions
    Returns list of dicts with keys: name, config_file, current_version, deployed_version
    """
    devices = []
    
    yaml_files = sorted(ESPHOME_DIR.glob("*.yaml"))
    log_verbose(f"Scanning {len(yaml_files)} YAML configuration files...")
    
    for yaml_path in yaml_files:
        yaml_name = yaml_path.name
        
        # Get device name from YAML
        device_name = get_device_name_from_yaml(yaml_path)
        if not device_name:
            log_debug(f"Skipping {yaml_name}: no device name found")
            continue
        
        # Get current version
        current_version = get_current_version(yaml_path)
        
        # Get deployed version from dashboard.json
        deployed_version, _ = get_dashboard_versions(device_name)
        
        devices.append({
            "name": device_name,
            "config_file": yaml_name,
            "current_version": current_version,
            "deployed_version": deployed_version,
        })
        
        log_debug(f"Device: {device_name} | Config: {yaml_name} | Current: {current_version or 'unknown'} | Deployed: {deployed_version or 'unknown'}")
    
    return devices

def get_device_name_from_yaml(yaml_path: Path) -> Optional[str]:
    """Extract device name from YAML config"""
    try:
        with yaml_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("name:") or line.startswith("device_name:"):
                    # Handle: name: my-device or name: "my-device"
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        name = parts[1].strip().strip('"').strip("'")
                        return name
    except Exception as e:
        log_debug(f"Error reading {yaml_path.name}: {e}")
    return None

def get_current_version(yaml_path: Path) -> Optional[str]:
    """Get current ESPHome version for a config"""
    # The path inside the container
    container_path = f"/config/esphome/{yaml_path.name}"
    
    returncode, stdout, stderr = run_esphome_command(
        ["version", container_path]
    )
    
    if returncode == 0:
        # Parse version from output
        for line in stdout.split("\n"):
            if "Version:" in line:
                version = line.split("Version:", 1)[1].strip()
                return version
    
    log_debug(f"Could not determine current version for {yaml_path.name}")
    return None

def compile_device(yaml_path: Path, opts: Dict) -> Tuple[bool, str]:
    """
    Compile ESPHome configuration
    Returns: (success, error_message)
    """
    log_normal(f"  → Compiling {yaml_path.name}...")
    
    # The path inside the container is the same as on the host
    # because /config is mounted to both
    container_path = f"/config/esphome/{yaml_path.name}"
    
    returncode, stdout, stderr = run_esphome_command(
        ["compile", container_path]
    )
    
    # ALWAYS log compilation output in debug mode
    log_debug(f"Compilation return code: {returncode}")
    log_debug(f"Compilation stdout:\n{stdout}")
    log_debug(f"Compilation stderr:\n{stderr}")
    
    # Check for errors first
    if returncode != 0:
        error_msg = "Compilation failed"
        combined_output = stdout + stderr
        
        # Check for specific error types
        if "page not found" in combined_output.lower():
            error_msg = "Docker container error - check ESPHome container is running"
            log_normal(f"  ✗ {error_msg}")
            log_normal(f"     Docker stderr: {stderr[:200]}")
        elif "no such file" in combined_output.lower():
            error_msg = f"YAML file not found in container: {container_path}"
            log_normal(f"  ✗ {error_msg}")
        elif "Error" in combined_output or "ERROR" in combined_output:
            # Extract ALL error lines, not just the first
            error_lines = []
            for line in combined_output.split("\n"):
                if "ERROR" in line.upper() or "error" in line.lower():
                    error_lines.append(line.strip())
            
            if error_lines:
                error_msg = error_lines[0]  # Use first error as main message
                log_normal(f"  ✗ {error_msg}")
                # Show additional errors if verbose
                if len(error_lines) > 1:
                    log_verbose("  Additional errors:")
                    for err in error_lines[1:5]:  # Show up to 5 errors
                        log_verbose(f"    - {err}")
            else:
                # No specific error found, show raw output
                log_normal(f"  ✗ Compilation failed")
                log_normal(f"     Return code: {returncode}")
                if stderr:
                    log_normal(f"     Stderr: {stderr[:500]}")
                if stdout:
                    log_verbose(f"     Stdout: {stdout[:500]}")
        else:
            # Generic failure - show what we have
            log_normal(f"  ✗ Compilation failed (return code: {returncode})")
            if stderr:
                log_normal(f"     Stderr: {stderr[:500]}")
            if stdout and not stderr:
                log_normal(f"     Stdout: {stdout[:500]}")
        
        if opts.get("stop_on_compilation_error", True):
            return (False, error_msg)
        else:
            return (False, error_msg)
    
    # Check for warnings
    combined_output = stdout + stderr
    if "WARNING" in combined_output.upper():
        log_verbose("  ⚠ Compilation produced warnings")
        if opts.get("stop_on_compilation_warning", False):
            return (False, "Compilation warning (stop_on_compilation_warning enabled)")
    
    log_verbose("  ✓ Compilation successful")
    return (True, "")

def upload_device(yaml_path: Path, opts: Dict) -> Tuple[bool, str]:
    """
    Upload firmware to device via OTA
    Returns: (success, error_message)
    """
    log_normal(f"  → Uploading to device...")
    
    # The path inside the container
    container_path = f"/config/esphome/{yaml_path.name}"
    
    returncode, stdout, stderr = run_esphome_command(
        ["upload", "--device", "OTA", container_path]
    )
    
    log_debug(f"Upload return code: {returncode}")
    if stdout:
        log_debug(f"Upload stdout:\n{stdout}")
    if stderr:
        log_debug(f"Upload stderr:\n{stderr}")
    
    if returncode != 0:
        error_msg = "Upload failed"
        combined_output = stdout + stderr
        
        # Extract meaningful error
        if "Connection refused" in combined_output:
            error_msg = "Connection refused (device offline or wrong IP?)"
        elif "timeout" in combined_output.lower():
            error_msg = "Upload timeout (device unreachable?)"
        elif "page not found" in combined_output.lower():
            error_msg = "Docker container error - check ESPHome container is running"
        elif stderr:
            for line in stderr.split("\n"):
                if "ERROR" in line.upper() or "Error" in line:
                    error_msg = line.strip()
                    break
        
        log_normal(f"  ✗ {error_msg}")
        
        if opts.get("stop_on_upload_error", True):
            return (False, error_msg)
        else:
            return (False, error_msg)
    
    log_verbose("  ✓ Upload successful")
    return (True, "")

# ============================================================================
# REPAIR MODE - Dashboard Metadata Repair
# ============================================================================

def repair_dashboard_metadata(
    devices: List[Dict],
    skip_existing: bool = True
) -> Tuple[int, int]:
    """
    Repair dashboard metadata by compiling devices without OTA upload.
    This populates deployed_version and current_version in dashboard.json.
    
    Returns: (repaired_count, failed_count)
    """
    log_header("Dashboard Metadata Repair Mode")
    log_quiet("This mode compiles devices to populate dashboard.json metadata")
    log_quiet("NO OTA uploads will be performed")
    log_quiet("")
    
    if skip_existing:
        log_normal("Will skip devices that already have metadata")
    else:
        log_normal("Will recompile ALL devices regardless of existing metadata")
    
    log_quiet("")
    
    repaired = 0
    failed = 0
    skipped = 0
    
    total = len(devices)
    
    for idx, dev in enumerate(devices, start=1):
        name = dev["name"]
        yaml_name = dev["config_file"]
        
        log_normal(f"[{idx}/{total}] Checking: {name}")
        
        # Check if metadata exists
        deployed, current = get_dashboard_versions(name)
        
        if skip_existing and deployed is not None and current is not None:
            log_verbose(f"  ✓ Metadata exists: deployed={deployed}, current={current}")
            skipped += 1
            continue
        
        # Compile to generate metadata
        log_normal(f"  → Compiling {yaml_name} to generate metadata...")
        yaml_path = ESPHOME_DIR / yaml_name
        
        # Use a minimal options dict for compilation (no stopping on errors during repair)
        repair_opts = {
            "stop_on_compilation_warning": False,
            "stop_on_compilation_error": False,
        }
        
        compile_ok, compile_error = compile_device(yaml_path, repair_opts)
        
        if compile_ok:
            # Verify metadata was created
            deployed, current = get_dashboard_versions(name)
            if deployed is not None or current is not None:
                log_normal(f"  ✓ Metadata generated: deployed={deployed}, current={current}")
                repaired += 1
            else:
                log_normal(f"  ⚠ Compiled but metadata not populated")
                failed += 1
        else:
            log_normal(f"  ✗ Compilation failed: {compile_error}")
            failed += 1
        
        # Small delay between devices
        if idx < total:
            time.sleep(0.5)
    
    log_quiet("")
    log_header("Repair Summary")
    log_quiet(f"Total devices: {total}")
    log_quiet(f"Metadata repaired: {repaired}")
    log_quiet(f"Already had metadata: {skipped}")
    log_quiet(f"Failed: {failed}")
    log_quiet("")
    
    return (repaired, failed)

# ============================================================================
# FILTERING & SELECTION
# ============================================================================

def matches_pattern(text: str, patterns: List[str]) -> bool:
    """Check if text matches any of the given patterns"""
    if not patterns:
        return False
    
    for pattern in patterns:
        if not pattern:
            continue
        # Simple wildcard matching: * means any characters
        regex_pattern = pattern.replace("*", ".*")
        if re.search(regex_pattern, text, re.IGNORECASE):
            return True
    
    return False

def should_process_device(device: Dict, opts: Dict, progress: Dict) -> Tuple[bool, str]:
    """
    Determine if a device should be processed
    Returns: (should_process, reason_if_not)
    """
    name = device["name"]
    config = device["config_file"]
    current = device["current_version"]
    deployed = device["deployed_version"]
    
    # Check if already processed
    if name in progress.get("done", []):
        return (False, "already processed (in done list)")
    
    if name in progress.get("failed", []):
        return (False, "previously failed (in failed list)")
    
    if name in progress.get("skipped", []):
        return (False, "previously skipped (in skipped list)")
    
    # Device name filtering
    include_patterns = opts.get("device_name_patterns", [])
    exclude_patterns = opts.get("skip_device_name_patterns", [])
    
    if include_patterns:
        if not matches_pattern(name, include_patterns):
            return (False, f"device name doesn't match include patterns")
    
    if matches_pattern(name, exclude_patterns):
        return (False, f"device name matches exclude pattern")
    
    # YAML name filtering
    yaml_include = opts.get("yaml_name_patterns", [])
    yaml_exclude = opts.get("skip_yaml_name_patterns", [])
    
    if yaml_include:
        if not matches_pattern(config, yaml_include):
            return (False, f"config file doesn't match include patterns")
    
    if matches_pattern(config, yaml_exclude):
        return (False, f"config file matches exclude pattern")
    
    # Version-based logic
    if not deployed:
        if not opts.get("update_when_no_deployed_version", False):
            return (False, "no deployed version (update_when_no_deployed_version=false)")
    
    if current and deployed and current == deployed:
        if not opts.get("update_when_version_matches", False):
            return (False, f"versions match ({current})")
    
    return (True, "")

def filter_devices(devices: List[Dict], opts: Dict, progress: Dict) -> List[Dict]:
    """Filter devices based on configuration"""
    log_header("Filtering Devices")
    
    total = len(devices)
    log_normal(f"Total devices found: {total}")
    
    filtered = []
    skip_reasons = {}
    
    for device in devices:
        should_process, reason = should_process_device(device, opts, progress)
        
        if should_process:
            filtered.append(device)
            log_verbose(f"✓ {device['name']} - will process")
        else:
            log_verbose(f"✗ {device['name']} - {reason}")
            skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
    
    log_normal(f"Devices to process: {len(filtered)}")
    log_normal(f"Devices skipped: {total - len(filtered)}")
    
    if skip_reasons:
        log_verbose("")
        log_verbose("Skip reasons:")
        for reason, count in sorted(skip_reasons.items(), key=lambda x: -x[1]):
            log_verbose(f"  - {reason}: {count}")
    
    return filtered

# ============================================================================
# DEVICE PROCESSING
# ============================================================================

def process_devices(devices: List[Dict], opts: Dict, progress: Dict):
    """Process (compile and upload) filtered devices"""
    if not devices:
        log_normal("")
        log_normal("No devices to process.")
        return
    
    log_header("Processing Devices")
    
    total = len(devices)
    dry_run = opts.get("dry_run", False)
    
    if dry_run:
        log_normal("DRY RUN MODE - No actual compilation or upload will occur")
        log_normal("")
    
    for idx, device in enumerate(devices, start=1):
        name = device["name"]
        config = device["config_file"]
        current = device["current_version"]
        deployed = device["deployed_version"]
        
        log_normal("")
        log_normal(f"[{idx}/{total}] Processing: {name}")
        log_verbose(f"  Config: {config}")
        log_verbose(f"  Versions: deployed={deployed or 'unknown'}, current={current or 'unknown'}")
        
        yaml_path = ESPHOME_DIR / config
        
        if dry_run:
            log_normal("  → [DRY RUN] Would compile and upload")
            progress["done"].append(name)
            save_progress(progress)
            continue
        
        # Compile
        compile_ok, compile_error = compile_device(yaml_path, opts)
        if not compile_ok:
            log_normal(f"  ✗ Compilation failed: {compile_error}")
            progress["failed"].append(name)
            save_progress(progress)
            
            if opts.get("stop_on_compilation_error", True):
                log_normal("")
                log_normal("Stopping due to compilation error (stop_on_compilation_error=true)")
                break
            continue
        
        # Upload
        upload_ok, upload_error = upload_device(yaml_path, opts)
        if not upload_ok:
            log_normal(f"  ✗ Upload failed: {upload_error}")
            progress["failed"].append(name)
            save_progress(progress)
            
            if opts.get("stop_on_upload_error", True):
                log_normal("")
                log_normal("Stopping due to upload error (stop_on_upload_error=true)")
                break
            continue
        
        # Success
        log_normal(f"  ✓ Successfully updated {name}")
        progress["done"].append(name)
        save_progress(progress)

# ============================================================================
# SUMMARY & REPORTING
# ============================================================================

def print_summary(devices: List[Dict], filtered: List[Dict], progress: Dict, opts: Dict):
    """Print final summary of operation"""
    log_header("Summary")
    
    total = len(devices)
    processed = len(filtered)
    done = len(progress.get("done", []))
    failed = len(progress.get("failed", []))
    skipped = total - processed
    
    log_quiet(f"Total devices: {total}")
    log_quiet(f"Devices processed: {done}")
    log_quiet(f"Devices failed: {failed}")
    log_quiet(f"Devices skipped: {skipped}")
    
    if failed > 0:
        log_quiet("")
        log_quiet("Failed devices:")
        for name in progress.get("failed", []):
            log_quiet(f"  - {name}")
    
    if opts.get("dry_run", False):
        log_quiet("")
        log_quiet("This was a DRY RUN - no actual changes were made")
    
    log_quiet("")
    log_quiet(f"Log file: {LOG_FILE}")
    log_quiet(f"Progress file: {PROGRESS_FILE}")
    log_quiet("")

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main execution function"""
    # Load configuration
    opts = load_options()
    state = load_state()
    progress = load_progress()
    
    # Set log level FIRST before any logging
    set_log_level(opts.get("log_level", "normal"))
    
    # Housekeeping
    progress = perform_housekeeping(opts, state, progress)
    
    # Start main execution
    log_header(f"ESPHome Selective Updates v{os.environ.get('ADDON_VERSION', 'unknown')}")
    log_normal(f"Log level: {opts.get('log_level', 'normal')}")
    
    # Verify ESPHome container is accessible
    esphome_container = os.environ.get("ESPHOME_CONTAINER", "")
    if not esphome_container:
        log_quiet("")
        log_quiet("ERROR: ESPHOME_CONTAINER environment variable not set")
        log_quiet("This should be set by run.sh - check your startup script")
        sys.exit(1)
    
    log_verbose(f"Using ESPHome container: {esphome_container}")
    
    # Test Docker connectivity
    log_verbose("Testing Docker connectivity...")
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={esphome_container}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            log_quiet("")
            log_quiet(f"ERROR: Cannot communicate with Docker daemon")
            log_quiet(f"Docker error: {result.stderr}")
            sys.exit(1)
        
        if esphome_container not in result.stdout:
            log_quiet("")
            log_quiet(f"ERROR: ESPHome container '{esphome_container}' is not running")
            log_quiet(f"Running containers: {result.stdout.strip()}")
            log_quiet("Please start the ESPHome add-on first")
            sys.exit(1)
        
        log_verbose(f"✓ Docker connectivity verified")
    except Exception as e:
        log_quiet("")
        log_quiet(f"ERROR: Failed to verify Docker connectivity: {e}")
        sys.exit(1)
    
    # Safety checks
    if not verify_safe_operation():
        log_quiet("")
        log_quiet("Safety checks failed. Cannot continue.")
        sys.exit(1)
    
    # Get devices
    log_header("Discovering Devices")
    devices = get_esphome_devices()
    log_normal(f"Discovered {len(devices)} ESPHome devices")
    
    # ============================================================================
    # DEBUG TEST MODE - Test single device with full output
    # ============================================================================
    
    test_device = opts.get("debug_test_single_device", "")
    if test_device:
        log_quiet("")
        log_quiet("=" * 70)
        log_quiet(f"DEBUG TEST MODE - Testing device: {test_device}")
        log_quiet("=" * 70)
        log_quiet("")
        
        # Force debug logging
        set_log_level("debug")
        
        # Find the device
        target = None
        for dev in devices:
            if dev["name"] == test_device or dev["config_file"].startswith(test_device):
                target = dev
                break
        
        if not target:
            log_quiet(f"ERROR: Device '{test_device}' not found")
            log_quiet("Available devices:")
            for dev in devices[:10]:
                log_quiet(f"  - {dev['name']} ({dev['config_file']})")
            sys.exit(1)
        
        log_quiet(f"Found device: {target['name']}")
        log_quiet(f"Config file: {target['config_file']}")
        log_quiet("")
        
        # Test compilation
        yaml_path = ESPHOME_DIR / target["config_file"]
        test_opts = {"stop_on_compilation_error": False}
        
        log_quiet("Testing compilation with full debug output:")
        log_quiet("-" * 70)
        success, error = compile_device(yaml_path, test_opts)
        log_quiet("-" * 70)
        
        if success:
            log_quiet("✓ Compilation SUCCEEDED")
        else:
            log_quiet(f"✗ Compilation FAILED: {error}")
        
        log_quiet("")
        log_quiet("Check the output above for the actual error details")
        log_quiet("Once you see the error, you can fix the YAML or disable this test mode")
        
        return  # Exit after test
    
    # ============================================================================
    # REPAIR MODE
    # ============================================================================
    
    repair_mode = opts.get("repair_dashboard_metadata", False)
    if repair_mode:
        log_quiet("")
        log_quiet("=" * 70)
        log_quiet("REPAIR MODE ENABLED")
        log_quiet("=" * 70)
        log_quiet("")
        
        # Force verbose logging during repair to see errors
        original_log_level = CURRENT_LOG_LEVEL
        set_log_level("verbose")
        log_normal("Temporarily setting log level to VERBOSE for repair diagnostics")
        log_normal("")
        
        skip_existing = opts.get("repair_skip_existing_metadata", True)
        repaired, failed = repair_dashboard_metadata(devices, skip_existing)
        
        # Restore original log level
        set_log_level(opts.get("log_level", "normal"))
        
        log_quiet("")
        log_quiet("=" * 70)
        log_quiet("Repair mode complete.")
        log_quiet("=" * 70)
        log_quiet("")
        log_quiet("Next steps:")
        log_quiet("  1. Set 'repair_dashboard_metadata: false' in configuration")
        log_quiet("  2. Run add-on normally for smart updates")
        log_quiet("")
        
        return  # Exit after repair
    
    # ============================================================================
    # NORMAL UPDATE MODE
    # ============================================================================
    
    # Filter devices
    filtered_devices = filter_devices(devices, opts, progress)
    
    # Process devices
    process_devices(filtered_devices, opts, progress)
    
    # Print summary
    print_summary(devices, filtered_devices, progress, opts)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log_quiet("")
        log_quiet("Interrupted by user")
        sys.exit(130)
    except Exception as e:
        log_quiet("")
        log_quiet(f"FATAL ERROR: {e}")
        import traceback
        log_debug(traceback.format_exc())
        sys.exit(1)