#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ADDON_OPTIONS_PATH = Path("/data/options.json")
LOG_FILE = Path("/config/esphome_smart_update.log")
PROGRESS_FILE = Path("/config/esphome_update_progress.json")

DEFAULTS = {
    "ota_password": "",
    "skip_offline": True,
    "delay_between_updates": 3,
    "esphome_container": "addon_15ef4d2f_esphome"
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
        with ADDON_OPTIONS_PATH.open("r", encoding="utf-8") as f:
            loaded = json.load(f)
            for k in DEFAULTS:
                if k in loaded:
                    opts[k] = loaded[k]
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

def _resolve_docker_host() -> str:
    dh = os.environ.get("DOCKER_HOST", "").strip()
    if dh:
        return dh
    for path in ("/run/docker.sock", "/var/run/docker.sock"):
        if os.path.exists(path):
            return f"unix://{path}"
    return "unix:///var/run/docker.sock"  # last resort default

def _docker_env():
    env = os.environ.copy()
    env["DOCKER_HOST"] = _resolve_docker_host()
    return env

def docker_exec(container: str, cmd: list[str]) -> int:
    proc = subprocess.run(["docker", "exec", container] + cmd, env=_docker_env())
    return proc.returncode

def docker_cp(container: str, src: str, dst: str) -> int:
    proc = subprocess.run(["docker", "cp", f"{container}:{src}", dst], env=_docker_env())
    return proc.returncode

def ensure_paths():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

def discover_devices_via_esphome_dashboard() -> list[dict]:
    esphome_dir = Path("/config/esphome")
    devices = []
    for y in sorted(esphome_dir.glob("*.yaml")):
        devices.append({
            "name": y.stem,
            "config": y.name,
            "address": None
        })
    return devices

def read_versions_from_esphome(container: str, yaml_name: str) -> tuple[str, str]:
    # Placeholder: wire to your real version probe if desired
    rc = docker_exec(container, ["esphome", f"/config/esphome/{yaml_name}", "config"])
    deployed = "unknown"
    current = "unknown"
    return deployed, current

def compile_firmware(container: str, yaml_name: str, device_name: str) -> str | None:
    log(f"→ Compiling {yaml_name} in container")
    rc = docker_exec(container, ["esphome", f"/config/esphome/{yaml_name}", "compile"])
    if rc != 0:
        log(f"✗ Compilation failed for {device_name}")
        return None
    build_dir = f"/config/esphome/.esphome/build/{Path(yaml_name).stem}/"
    bin_name = f"{Path(yaml_name).stem}.bin"
    src_path = build_dir + bin_name
    dst_dir = "/config/esphome/builds"
    Path(dst_dir).mkdir(parents=True, exist_ok=True)
    dst_path = f"{dst_dir}/{bin_name}"
    if docker_cp(container, src_path, dst_path) != 0:
        log(f"✗ Could not copy binary for {device_name}")
        return None
    log(f"→ Binary copied to {dst_path}")
    return dst_path

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

def main():
    ensure_paths()
    opts = load_options()
    progress = load_progress()

    esphome_container = opts["esphome_container"]
    skip_offline = bool(opts["skip_offline"])
    delay = int(opts["delay_between_updates"])
    ota_password = str(opts["ota_password"])

    log("=" * 79)
    log("ESPHome Smart Updater Add-on")
    log("=" * 79)

    # Quick docker check (respects dynamic DOCKER_HOST)
    try:
        subprocess.check_call(["docker", "ps"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=_docker_env())
    except Exception as e:
        log("Error: Cannot connect to Docker via client.")
        log(f"Detail: {e}")
        log("Hint: Supervisor must mount a socket; ensure 'docker_api': true.")
        sys.exit(1)

    devices = discover_devices_via_esphome_dashboard()
    total = len(devices)
    log(f"Found {total} total devices to consider")

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

        needs_update = True  # plug in your real decision logic
        if not needs_update:
            progress["skipped"].append(name)
            save_progress(progress)
            continue

        if skip_offline and address and not ping_host(address):
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