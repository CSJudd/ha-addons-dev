#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple

ADDON_OPTIONS_PATH = Path("/data/options.json")
LOG_FILE = Path("/config/esphome_smart_update.log")
PROGRESS_FILE = Path("/config/esphome_update_progress.json")

DEFAULTS = {
    "ota_password": "",
    "skip_offline": True,
    "delay_between_updates": 3,
    "compile_mode": "auto",
    "esphome_container": "addon_15ef4d2f_esphome",
}

def ts() -> str:
    return datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")

def log(msg: str):
    line = f"{ts()} {msg}"
    print(line, flush=True)
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def load_options():
    opts = DEFAULTS.copy()
    if ADDON_OPTIONS_PATH.exists():
      try:
        with ADDON_OPTIONS_PATH.open("r", encoding="utf-8") as f:
            loaded = json.load(f)
        for k in DEFAULTS:
            if k in loaded:
                opts[k] = loaded[k]
      except Exception as e:
          log(f"Warning: failed to parse options.json: {e}")
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
        log(f"Warning: failed to write progress: {e}")

def ensure_paths():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

def ping_host(host: str, count: int = 1, timeout: int = 1) -> bool:
    try:
        res = subprocess.run(
            ["ping", "-c", str(count), "-W", str(timeout), host],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return res.returncode == 0
    except FileNotFoundError:
        return True

# ---------- discovery/versioning stubs (plug in your own if you have them) ----------
def discover_devices() -> List[dict]:
    esphome_dir = Path("/config/esphome")
    devices = []
    for y in sorted(esphome_dir.glob("*.yaml")):
        devices.append({"name": y.stem, "config": y.name, "address": None})
    return devices

def read_versions(_, __) -> Tuple[str, str]:
    # Placeholder: wire up to your version inventory if available
    return ("unknown", "unknown")

# ---------- compile/upload backends ----------
def _docker_env():
    env = os.environ.copy()
    # DOCKER_HOST set by run.sh if docker path is usable; not required here
    return env

def compile_via_docker(container: str, yaml_name: str, device_name: str) -> Optional[str]:
    log(f"→ [docker] Compiling {yaml_name} in {container}")
    rc = subprocess.run(
        ["docker", "exec", container, "esphome", f"/config/esphome/{yaml_name}", "compile"],
        env=_docker_env()
    ).returncode
    if rc != 0:
        log(f"✗ Compilation failed for {device_name}")
        return None

    build_dir = f"/config/esphome/.esphome/build/{Path(yaml_name).stem}/"
    bin_name = f"{Path(yaml_name).stem}.bin"
    src_path = build_dir + bin_name
    dst_dir = "/config/esphome/builds"
    Path(dst_dir).mkdir(parents=True, exist_ok=True)
    dst_path = f"{dst_dir}/{bin_name}"

    rc = subprocess.run(["docker", "cp", f"{container}:{src_path}", dst_path], env=_docker_env()).returncode
    if rc != 0:
        log(f"✗ Could not copy binary for {device_name}")
        return None

    log(f"→ [docker] Binary copied to {dst_path}")
    return dst_path

def compile_via_builtin(yaml_name: str, device_name: str) -> Optional[str]:
    esphome_bin = os.environ.get("ESPHOME_BIN", "/data/venv/bin/esphome")
    if not Path(esphome_bin).exists():
        log("✗ Built-in esphome binary not found (ESPHOME_BIN).")
        return None

    log(f"→ [builtin] Compiling {yaml_name} using {esphome_bin}")
    rc = subprocess.run(
        [esphome_bin, f"/config/esphome/{yaml_name}", "compile"]
    ).returncode
    if rc != 0:
        log(f"✗ Compilation failed for {device_name}")
        return None

    # Built-in compile output path is identical to ESPHome container
    build_dir = f"/config/esphome/.esphome/build/{Path(yaml_name).stem}/"
    bin_name = f"{Path(yaml_name).stem}.bin"
    src_path = Path(build_dir) / bin_name
    dst_dir = Path("/config/esphome/builds")
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst_path = dst_dir / bin_name

    try:
        data = src_path.read_bytes()
        dst_path.write_bytes(data)
    except Exception as e:
        log(f"✗ Could not copy binary for {device_name}: {e}")
        return None

    log(f"→ [builtin] Binary copied to {dst_path}")
    return str(dst_path)

def ota_upload(bin_path: str, address: str, ota_password: str) -> bool:
    try:
        import requests
        url = f"http://{address}/ota"
        with open(bin_path, "rb") as f:
            r = requests.post(url, params={"password": ota_password}, data=f, timeout=300)
        return 200 <= r.status_code < 300
    except Exception as e:
        log(f"OTA error: {e}")
        return False

# ---------- main ----------
def main():
    ensure_paths()
    opts = load_options()
    progress = load_progress()

    mode = os.environ.get("SMART_UPDATER_MODE", "builtin")  # set by run.sh
    esphome_container = os.environ.get("SMART_UPDATER_ESPHOME_CONTAINER", opts["esphome_container"])

    log("=" * 79)
    log("ESPHome Smart Updater Add-on")
    log(f"Mode: {mode}")
    log("=" * 79)

    # Discovery
    devices = discover_devices()
    total = len(devices)
    log(f"Found {total} total devices to consider")

    progress.setdefault("done", [])
    progress.setdefault("failed", [])
    progress.setdefault("skipped", [])

    # Settings
    skip_offline = bool(opts["skip_offline"])
    delay = int(opts["delay_between_updates"])
    ota_password = str(opts["ota_password"])

    for idx, dev in enumerate(devices, start=1):
        name = dev["name"]
        yaml_name = dev["config"]
        addr = dev["address"]

        if name in progress["done"]:
            continue

        log("")
        log(f"[{idx}/{total}] Processing: {name}")
        log(f"Config: {yaml_name}")
        if addr:
            log(f"Address: {addr}")

        deployed, current = read_versions(esphome_container, yaml_name)
        log(f"Deployed: {deployed} | Current: {current}")

        # Decision stub (always update for now)
        needs_update = True
        if not needs_update:
            progress["skipped"].append(name)
            save_progress(progress)
            continue

        if skip_offline and addr and not ping_host(addr):
            log(f"Device offline; skipping: {name}")
            progress["skipped"].append(name)
            save_progress(progress)
            continue

        log(f"Starting update for {name}")
        if mode == "docker":
            bin_path = compile_via_docker(esphome_container, yaml_name, name)
        else:
            bin_path = compile_via_builtin(yaml_name, name)

        if not bin_path:
            progress["failed"].append(name)
            save_progress(progress)
            continue

        ok = True
        if addr:
            ok = ota_upload(bin_path, addr, ota_password)

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