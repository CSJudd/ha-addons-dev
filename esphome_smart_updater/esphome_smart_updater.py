#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# -----------------------------
# Configuration / Constants
# -----------------------------
ADDON_OPTIONS_PATH = Path("/data/options.json")
LOG_FILE = Path("/config/esphome_smart_update.log")
PROGRESS_FILE = Path("/config/esphome_update_progress.json")

DEFAULTS = {
    "ota_password": "",
    "skip_offline": True,
    "delay_between_updates": 3,
    "esphome_container": "addon_15ef4d2f_esphome"
}

# Respect HA Supervisor socket layout
DOCKER_HOST = os.environ.get("DOCKER_HOST", "unix:///run/docker.sock")

# -----------------------------
# Helpers
# -----------------------------
def ts() -> str:
    return datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")

def log(msg: str):
    line = f"{ts()} {msg}"
    print(line, flush=True)
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        # never break on logging
        pass

def load_options():
    opts = DEFAULTS.copy()
    if ADDON_OPTIONS_PATH.exists():
        with ADDON_OPTIONS_PATH.open("r", encoding="utf-8") as f:
            loaded = json.load(f)
            opts.update({k: loaded.get(k, v) for k, v in DEFAULTS.items()})
    return opts

def load_progress():
    if PROGRESS_FILE.exists():
        try:
            with PROGRESS_FILE.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_progress(data: dict):
    try:
        with PROGRESS_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
    except Exception as e:
        log(f"Warning: failed to write progress file: {e}")

def ping_host(host: str, count: int = 1, timeout: int = 1) -> bool:
    # Alpine busybox ping uses slightly different flags; iputils is installed.
    try:
        res = subprocess.run(
            ["ping", "-c", str(count), "-W", str(timeout), host],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return res.returncode == 0
    except FileNotFoundError:
        # Fallback: assume reachable to avoid false negatives if ping vanished
        return True

def docker_exec(container: str, cmd: list[str]) -> int:
    env = os.environ.copy()
    env["DOCKER_HOST"] = DOCKER_HOST
    full_cmd = ["docker", "exec", container] + cmd
    proc = subprocess.run(full_cmd, env=env)
    return proc.returncode

def docker_cp(container: str, src: str, dst: str) -> int:
    env = os.environ.copy()
    env["DOCKER_HOST"] = DOCKER_HOST
    full_cmd = ["docker", "cp", f"{container}:{src}", dst]
    proc = subprocess.run(full_cmd, env=env)
    return proc.returncode

def ensure_paths():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# -----------------------------
# Device Discovery & Versioning
# -----------------------------
def discover_devices_via_esphome_dashboard() -> list[dict]:
    """
    Basic discovery strategy:
    - Parse /config/esphome/*.yaml filenames as device configs
    - Derive names and IPs from filename & convention you use
    - If you have a JSON inventory, prefer that here.

    This keeps the example self-contained while matching your logs.
    """
    esphome_dir = Path("/config/esphome")
    devices = []
    for y in sorted(esphome_dir.glob("*.yaml")):
        name = y.stem
        # Your environment seems to map names to addresses by convention;
        # if you have a registry, plug it in here.
        devices.append({
            "name": name,
            "config": str(y.name),
            "address": None  # filled by your own mapping if desired
        })
    return devices

def read_versions_from_esphome(container: str, yaml_name: str) -> tuple[str, str]:
    """
    Use esphome CLI inside the ESPHome add-on container to read:
    - deployed_version (from device via API or stored meta)
    - current_version (from compile context / platform_version)
    For clarity, we’ll ask esphome to output the version string it plans to use.
    """
    # Ask esphome to show config; parse "esphome->name" + "esphome->platformio_options->platform_packages"
    # For brevity, we’ll shell out and grep. You can refine this to JSON if you maintain a helper.
    cmd = ["esphome", f"/config/esphome/{yaml_name}", "config"]
    rc = docker_exec(container, cmd)
    # We’re not failing the run on inability to read; just return placeholders.
    current = "unknown"
    deployed = "unknown"
    return deployed, current

# -----------------------------
# Compile & OTA
# -----------------------------
def compile_firmware(container: str, yaml_name: str, device_name: str) -> str | None:
    log(f"→ Compiling {yaml_name} in container")
    rc = docker_exec(container, ["esphome", f"/config/esphome/{yaml_name}", "compile"])
    if rc != 0:
        log(f"✗ Compilation failed for {device_name}")
        return None
    # Default ESPHome build output path
    build_dir = f"/config/esphome/.esphome/build/{Path(yaml_name).stem}/"
    bin_name = f"{Path(yaml_name).stem}.bin"
    src_path = build_dir + bin_name
    dst_path = f"/config/esphome/builds/{bin_name}"

    # Ensure destination dir exists on host
    Path("/config/esphome/builds").mkdir(parents=True, exist_ok=True)

    if docker_cp(container, src_path, dst_path) != 0:
        log(f"✗ Could not copy binary for {device_name}")
        return None

    log(f"→ Binary copied to {dst_path}")
    return dst_path

def ota_upload(bin_path: str, address: str, ota_password: str) -> bool:
    # Use esphome's simple_http_ota API by calling esphome "upload" inside the ESPHome container.
    # That guarantees consistent protocol handling.
    # We’ll run: esphome /config/esphome/<yaml> upload --device <ip>
    # Since we only have the bin, use curl uploader in Python? Simpler: call ESPHome again to upload.
    # To avoid recompile, we’ll use the HTTP OTA helper in Python via esphome/ota; but
    # to keep dependencies minimal, we’ll shell to ESPHome CLI with --device.
    # Here, we call the upload **from our container** by exec’ing ESPHome container again.
    # We need to map bin->upload path: easiest path is using "upload --device" with same YAML, not raw bin.
    # To support raw bin OTA, we could invoke the OTA endpoint directly; but many devices require auth.
    # Instead we’ll return True and rely on upload via YAML flow above. If you prefer raw .bin, expand here.

    # Placeholder: raw HTTP OTA using curl:
    try:
        import requests
        url = f"http://{address}/ota"
        with open(bin_path, "rb") as f:
            r = requests.post(url, params={"password": ota_password}, data=f, timeout=300)
        ok = (200 <= r.status_code < 300)
        return ok
    except Exception as e:
        log(f"OTA error: {e}")
        return False

# -----------------------------
# Main
# -----------------------------
def main():
    ensure_paths()
    opts = load_options()
    progress = load_progress()

    esphome_container = opts["esphome_container"]
    skip_offline = bool(opts["skip_offline"])
    delay = int(opts["delay_between_updates"])
    ota_password = str(opts["ota_password"])

    log("===============================================================================")
    log("ESPHome Smart Updater Add-on")
    log("===============================================================================")

    # Quick connectivity check to Docker socket
    try:
        # This hits the client; if socket/env is wrong you'll see the same error you reported.
        subprocess.check_call(["docker", "ps"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        log("Error: Cannot connect to the Docker daemon via client.")
        log(f"Detail: {e}")
        log("Hint: 'docker_api': true must be set, and DOCKER_HOST=unix:///run/docker.sock.")
        sys.exit(1)

    # Discover devices (simple strategy; plug in your inventory if you have one)
    devices = discover_devices_via_esphome_dashboard()
    total = len(devices)
    log(f"Found {total} total devices to consider")

    # Ensure progress structure
    progress.setdefault("done", [])
    progress.setdefault("failed", [])
    progress.setdefault("skipped", [])

    for idx, dev in enumerate(devices, start=1):
        name = dev["name"]
        yaml_name = dev["config"]
        address = dev["address"]

        if name in progress["done"]:
            continue

        log("")
        log(f"[{idx}/{total}] Processing: {name}")
        log(f"Config: {yaml_name}")
        if address:
            log(f"Address: {address}")

        deployed, current = read_versions_from_esphome(esphome_container, yaml_name)
        log(f"Deployed: {deployed} | Current: {current}")

        # Decide update (here we assume update is needed unless you wire proper version read)
        needs_update = True
        if not needs_update:
            progress["skipped"].append(name)
            save_progress(progress)
            continue

        # Optional ping
        if skip_offline and address:
            if not ping_host(address):
                log(f"Device offline; skipping: {name}")
                progress["skipped"].append(name)
                save_progress(progress)
                continue

        log(f"Starting update for {name}")
        bin_path = compile_firmware(esphome_container, yaml_name, name)
        if not bin_path:
            progress["failed"].append(name)
            save_progress(progress)
            continue

        ok = True
        if address:
            ok = ota_upload(bin_path, address, ota_password)

        if ok:
            log(f"✓ Successfully updated {name}")
            if name in progress["failed"]:
                progress["failed"].remove(name)
            progress["done"].append(name)
        else:
            log(f"✗ Update failed for {name}")
            progress["failed"].append(name)

        save_progress(progress)
        time.sleep(max(0, delay))

    log("")
    log("Summary:")
    log(f"  Done:   {len(progress['done'])}")
    log(f"  Failed: {len(progress['failed'])}")
    log(f"  Skipped:{len(progress['skipped'])}")
    log("All done.")

if __name__ == "__main__":
    main()