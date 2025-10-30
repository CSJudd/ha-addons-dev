#!/usr/bin/env python3
import json, os, signal, subprocess, sys, time, shlex
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
    "esphome_container": "addon_15ef4d2f_esphome",
}

STOP_REQUESTED = False
CURRENT_CHILD: Optional[subprocess.Popen] = None

def ts() -> str: return datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")

def log(msg: str):
    line = f"{ts()} {msg}"
    print(line, flush=True)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def _sig_handler(signum, frame):
    global STOP_REQUESTED, CURRENT_CHILD
    STOP_REQUESTED = True
    if CURRENT_CHILD and CURRENT_CHILD.poll() is None:
        try:
            os.killpg(os.getpgid(CURRENT_CHILD.pid), signal.SIGTERM)
        except Exception:
            try: CURRENT_CHILD.terminate()
            except Exception: pass

signal.signal(signal.SIGTERM, _sig_handler)
signal.signal(signal.SIGINT, _sig_handler)

def load_options():
    opts = DEFAULTS.copy()
    if ADDON_OPTIONS_PATH.exists():
        try:
            loaded = json.loads(ADDON_OPTIONS_PATH.read_text(encoding="utf-8"))
            for k in DEFAULTS:
                if k in loaded:
                    opts[k] = loaded[k]
        except Exception as e:
            log(f"Warning: options.json parse error: {e}")
    return opts

def load_progress():
    if PROGRESS_FILE.exists():
        try: return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        except Exception: return {}
    return {}

def save_progress(data: dict):
    try:
        PROGRESS_FILE.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    except Exception as e:
        log(f"Warning: failed to write progress: {e}")

def ping_host(host: str, count: int = 1, timeout: int = 1) -> bool:
    try:
        rc = subprocess.run(
            ["ping","-c",str(count),"-W",str(timeout),host],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ).returncode
        return rc == 0
    except FileNotFoundError:
        return True  # don’t block if ping missing

def discover_devices() -> List[dict]:
    esphome_dir = Path("/config/esphome")
    return [{"name": y.stem, "config": y.name, "address": None}
            for y in sorted(esphome_dir.glob("*.yaml"))]

def read_versions(_, __) -> Tuple[str,str]:
    return ("unknown","unknown")

# ---------- docker helpers ----------

def _run(cmd: list[str], env: Optional[dict]=None) -> int:
    global CURRENT_CHILD
    if STOP_REQUESTED: return 143
    try:
        CURRENT_CHILD = subprocess.Popen(cmd, env=env, preexec_fn=os.setsid)
        rc = CURRENT_CHILD.wait()
        return rc
    finally:
        CURRENT_CHILD = None

def _run_out(cmd: list[str], env: Optional[dict]=None) -> tuple[int,str,str]:
    if STOP_REQUESTED: return (143,"","")
    p = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return (p.returncode, p.stdout, p.stderr)

def docker_exec(container: str, args: list[str]) -> int:
    return _run(["docker","exec",container] + args, os.environ.copy())

def docker_exec_out(container: str, args: list[str]) -> tuple[int,str,str]:
    return _run_out(["docker","exec",container] + args, os.environ.copy())

def docker_exec_shell_out(container: str, shell_cmd: str) -> tuple[int,str,str]:
    return _run_out(["docker","exec",container,"sh","-lc",shell_cmd], os.environ.copy())

def docker_cp(src_container: str, src_path: str, dst_path: str) -> int:
    return _run(["docker","cp",f"{src_container}:{src_path}", dst_path], os.environ.copy())

def docker_file_exists(container: str, filepath: str) -> bool:
    return docker_exec(container, ["test","-f",filepath]) == 0

def docker_dir_exists(container: str, dirpath: str) -> bool:
    return docker_exec(container, ["test","-d",dirpath]) == 0

# ---------- firmware path discovery ----------

def _first_existing_firmware_path(container: str, stem: str) -> Optional[str]:
    """
    Priority:
      A) New ESPHome (inside add-on): /data/build/<name>/.pioenvs/<name>/firmware.bin
         - Prefer entries whose /data/build/<name> starts with "<stem>-"
      B) New old-style copies:        /config/esphome/build/<stem>/<stem>.bin
      C) Legacy pre-2025.9:           /config/esphome/.esphome/build/<stem>/<stem>.bin
    """

    # A) probe /data/build/*/.pioenvs/*/firmware.bin and prefer ones matching "<stem>-"
    rc, out, _ = docker_exec_shell_out(
        container,
        r'ls -1d /data/build/*/.pioenvs/*/firmware.bin 2>/dev/null || true'
    )
    candidates = [p for p in out.strip().splitlines() if p]

    def score(p: str) -> int:
        # best if starts with /data/build/<stem>-
        try:
            name_dir = p.split("/data/build/")[1].split("/.pioenvs/")[0]
        except Exception:
            name_dir = ""
        if name_dir.startswith(f"{stem}-"):
            return 2
        if stem in name_dir:
            return 1
        return 0

    if candidates:
        candidates.sort(key=score, reverse=True)
        if score(candidates[0]) > 0 or candidates:
            return candidates[0]

    # B) newer non-/data path we tried earlier
    new_bin = f"/config/esphome/build/{stem}/{stem}.bin"
    if docker_file_exists(container, new_bin):
        return new_bin

    # C) legacy
    old_bin = f"/config/esphome/.esphome/build/{stem}/{stem}.bin"
    if docker_file_exists(container, old_bin):
        return old_bin

    # last-ditch: any *.bin under those device dirs
    for dir_try in (f"/config/esphome/build/{stem}", f"/config/esphome/.esphome/build/{stem}"):
        if docker_dir_exists(container, dir_try):
            rc2, out2, _ = docker_exec_shell_out(container, f'ls -1 {shlex.quote(dir_try)}/*.bin 2>/dev/null | head -n1')
            cand = out2.strip()
            if rc2 == 0 and cand:
                return cand

    return None

# ---------- compile + copy ----------

def compile_in_esphome_container(container: str, yaml_name: str, device_name: str) -> Optional[str]:
    log(f"→ Compiling {yaml_name} via docker in '{container}'")
    rc = docker_exec(container, ["esphome","compile",f"/config/esphome/{yaml_name}"])
    if rc != 0 or STOP_REQUESTED:
        if STOP_REQUESTED: log("Stop requested; aborting compile.")
        else: log(f"✗ Compilation failed for {device_name}")
        return None

    stem = Path(yaml_name).stem
    firmware_path = _first_existing_firmware_path(container, stem)
    if not firmware_path:
        log(f"✗ Could not locate firmware binary for {device_name} (checked /data and legacy paths)")
        return None

    dst_dir = Path("/config/esphome/builds")
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst_path = str(dst_dir / f"{stem}.bin")

    rc = docker_cp(container, firmware_path, dst_path)
    if rc != 0:
        log(f"✗ Could not copy binary for {device_name} from {firmware_path}")
        return None

    log(f"→ Binary copied to {dst_path} (from {firmware_path})")
    return dst_path

# ---------- OTA ----------

def ota_upload(bin_path: str, address: str, ota_password: str) -> bool:
    try:
        import requests
        url = f"http://{address}/ota"
        with open(bin_path,"rb") as f:
            r = requests.post(url, params={"password": ota_password}, data=f, timeout=300)
        if 200 <= r.status_code < 300:
            return True
        log(f"OTA HTTP {r.status_code}: {r.text[:200]}")
        return False
    except Exception as e:
        log(f"OTA error: {e}")
        return False

# ---------- main ----------

def main():
    opts = load_options()
    progress = load_progress()

    esphome_container = opts["esphome_container"]
    skip_offline = bool(opts["skip_offline"])
    delay = int(opts["delay_between_updates"])
    ota_password = str(opts["ota_password"])

    log("="*79)
    log("ESPHome Smart Updater (Docker exec mode)")
    log("="*79)

    devices = discover_devices()
    total = len(devices)
    log(f"Found {total} total devices to consider")

    progress.setdefault("done", [])
    progress.setdefault("failed", [])
    progress.setdefault("skipped", [])

    for idx, dev in enumerate(devices, start=1):
        if STOP_REQUESTED:
            log("Stop requested; saving progress and exiting.")
            break

        name = dev["name"]; yaml_name = dev["config"]; addr = dev["address"]

        if name in progress["done"]:
            continue

        log(""); log(f"[{idx}/{total}] Processing: {name}")
        log(f"Config: {yaml_name}")
        if addr: log(f"Address: {addr}")

        deployed,current = read_versions(esphome_container, yaml_name)
        log(f"Deployed: {deployed} | Current: {current}")

        needs_update = True  # wire your real comparison when ready
        if not needs_update:
            progress["skipped"].append(name); save_progress(progress); continue

        if skip_offline and addr and not ping_host(addr):
            log(f"Device offline; skipping: {name}")
            progress["skipped"].append(name); save_progress(progress); continue

        log(f"Starting update for {name}")
        bin_path = compile_in_esphome_container(esphome_container, yaml_name, name)

        if STOP_REQUESTED:
            log("Stop requested during compile; saving progress and exiting.")
            break

        if not bin_path:
            progress["failed"].append(name); save_progress(progress); continue

        ok = True
        if addr:
            ok = ota_upload(bin_path, addr, ota_password)

        if ok:
            log(f"✓ Successfully updated {name}")
            if name in progress["failed"]: progress["failed"].remove(name)
            progress["done"].append(name)
        else:
            log(f"✗ Update failed for {name}")
            progress["failed"].append(name)

        save_progress(progress)

        for _ in range(max(0, delay)):
            if STOP_REQUESTED: break
            time.sleep(1)
        if STOP_REQUESTED:
            log("Stop requested after delay; saving progress and exiting.")
            break

    log(""); log("Summary:")
    log(f"  Done:   {len(progress['done'])}")
    log(f"  Failed: {len(progress['failed'])}")
    log(f"  Skipped:{len(progress['skipped'])}")
    log("All done.")
    save_progress(progress)

if __name__ == "__main__":
    main()