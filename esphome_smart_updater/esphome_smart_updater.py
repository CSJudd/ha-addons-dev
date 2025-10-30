#!/usr/bin/env python3
import json, os, signal, subprocess, sys, time, shlex, ipaddress
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple

ADDON_OPTIONS_PATH = Path("/data/options.json")
LOG_FILE = Path("/config/esphome_smart_update.log")
PROGRESS_FILE = Path("/config/esphome_update_progress.json")
DASHBOARD_JSON_HOST = Path("/config/esphome/.esphome/dashboard.json")

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

def _load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def load_progress():
    data = _load_json(PROGRESS_FILE, {})
    # normalize + dedupe to prevent runaway counts
    for k in ("done","failed","skipped"):
        v = data.get(k, [])
        if isinstance(v, list):
            data[k] = list(dict.fromkeys(v))  # order preserving dedupe
        else:
            data[k] = []
    return data

def save_progress(data: dict):
    # ensure dedupe on write too
    for k in ("done","failed","skipped"):
        v = data.get(k, [])
        data[k] = list(dict.fromkeys(v)) if isinstance(v, list) else []
    try:
        PROGRESS_FILE.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    except Exception as e:
        log(f"Warning: failed to write progress: {e}")

def ping_ip(ip: str, count: int = 1, timeout: int = 1) -> bool:
    try:
        rc = subprocess.run(["ping","-c",str(count),"-W",str(timeout),ip],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
        return rc == 0
    except FileNotFoundError:
        # If ping is missing, don’t block updates
        return True

def _is_ip(s: str) -> bool:
    try:
        ipaddress.ip_address(s)
        return True
    except Exception:
        return False

# ---------------- Docker helpers ----------------

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

# ---------------- Dashboard address map ----------------

def _read_dashboard_map_from_host() -> dict:
    m: dict[str, dict] = {}
    if not DASHBOARD_JSON_HOST.exists():
        return m
    try:
        data = json.loads(DASHBOARD_JSON_HOST.read_text(encoding="utf-8"))
        items = data if isinstance(data, list) else data.get("entries") or []
        for entry in items:
            cfg = (entry.get("configuration") or "").strip()
            addr = (entry.get("address") or "").strip()
            name = (entry.get("name") or "").strip()
            if not cfg:
                continue
            base = Path(cfg).name
            m[base] = {"address": addr, "name": name}
    except Exception as e:
        log(f"Warning: failed to parse host dashboard.json: {e}")
    return m

def _read_dashboard_map_from_container(container: str) -> dict:
    """
    Read /data/dashboard.json from the ESPHome container — this file is authoritative
    for current device addresses as shown in the dashboard UI.
    """
    m: dict[str, dict] = {}
    rc, out, err = docker_exec_shell_out(container, 'cat /data/dashboard.json 2>/dev/null || true')
    if rc != 0 or not out.strip():
        return m
    try:
        data = json.loads(out)
        items = data if isinstance(data, list) else data.get("entries") or []
        for entry in items:
            cfg = (entry.get("configuration") or "").strip()
            addr = (entry.get("address") or "").strip()
            name = (entry.get("name") or "").strip()
            if not cfg:
                continue
            base = Path(cfg).name
            m[base] = {"address": addr, "name": name}
    except Exception as e:
        log(f"Warning: failed to parse container dashboard.json: {e}")
    return m

def read_address_map(esphome_container: str) -> dict:
    m = _read_dashboard_map_from_host()
    if not m:
        m = _read_dashboard_map_from_container(esphome_container)
    return m

# ---------------- Firmware path discovery ----------------

def _pull_name_from_data_build_path(p: str) -> str:
    # /data/build/<name>/.pioenvs/<name>/firmware.bin
    try:
        return p.split("/data/build/")[1].split("/.pioenvs/")[0]
    except Exception:
        return ""

def _score_candidate(stem: str, name: str) -> int:
    if name.startswith(f"{stem}-"): return 3
    if name == stem: return 2
    if stem in name: return 1
    return 0

def _find_firmware_and_esphome_name(container: str, stem: str) -> Tuple[Optional[str], Optional[str]]:
    # Preferred: modern /data paths
    rc, out, _ = docker_exec_shell_out(
        container,
        r'ls -1d /data/build/*/.pioenvs/*/firmware.bin 2>/dev/null || true'
    )
    candidates = [p for p in out.strip().splitlines() if p]
    if candidates:
        candidates.sort(key=lambda p: _score_candidate(stem, _pull_name_from_data_build_path(p)), reverse=True)
        best = candidates[0]
        esphome_name = _pull_name_from_data_build_path(best)
        return best, esphome_name or stem

    # New local path
    new_bin = f"/config/esphome/build/{stem}/{stem}.bin"
    if docker_file_exists(container, new_bin):
        return new_bin, stem

    # Legacy local path
    old_bin = f"/config/esphome/.esphome/build/{stem}/{stem}.bin"
    if docker_file_exists(container, old_bin):
        return old_bin, stem

    # Wildcard last resort
    for d in (f"/config/esphome/build/{stem}", f"/config/esphome/.esphome/build/{stem}"):
        if docker_dir_exists(container, d):
            rc2, out2, _ = docker_exec_shell_out(container, f'ls -1 {shlex.quote(d)}/*.bin 2>/dev/null | head -n1')
            cand = out2.strip()
            if rc2 == 0 and cand:
                return cand, stem

    return None, None

# ---------------- Compile + Upload ----------------

def compile_in_esphome_container(container: str, yaml_name: str, device_name: str) -> Tuple[Optional[str], Optional[str]]:
    log(f"→ Compiling {yaml_name} via docker in '{container}'")
    rc = docker_exec(container, ["esphome","compile",f"/config/esphome/{yaml_name}"])
    if rc != 0 or STOP_REQUESTED:
        if STOP_REQUESTED: log("Stop requested; aborting compile.")
        else: log(f"✗ Compilation failed for {device_name}")
        return None, None

    stem = Path(yaml_name).stem
    firmware_path, esphome_name = _find_firmware_and_esphome_name(container, stem)
    if not firmware_path:
        log(f"✗ Could not locate firmware binary for {device_name} (checked /data and legacy paths)")
        return None, None

    dst_dir = Path("/config/esphome/builds"); dst_dir.mkdir(parents=True, exist_ok=True)
    dst_path = str(dst_dir / f"{stem}.bin")

    rc = docker_cp(container, firmware_path, dst_path)
    if rc != 0:
        log(f"✗ Could not copy binary for {device_name} from {firmware_path}")
        return None, None

    log(f"→ Binary copied to {dst_path} (from {firmware_path})")
    return dst_path, esphome_name

def upload_via_esphome(container: str, yaml_name: str, target: str) -> bool:
    log(f"→ Uploading via ESPHome: {yaml_name} → {target}")
    rc, out, err = docker_exec_out(
        container,
        ["esphome","upload",f"/config/esphome/{yaml_name}","--device",target,"--no-logs"]
    )
    if rc == 0:
        log("→ OTA upload reported success.")
        return True
    tail = (out or err or "").strip().splitlines()[-20:]
    if tail:
        log("OTA uploader output (tail):")
        for line in tail:
            log(f"  {line}")
    return False

# ---------------- Discovery ----------------

def discover_devices() -> List[dict]:
    esphome_dir = Path("/config/esphome")
    return [{"name": y.stem, "config": y.name} for y in sorted(esphome_dir.glob("*.yaml"))]

def read_versions(_, __) -> Tuple[str,str]:
    return ("unknown","unknown")

# ---------------- Main ----------------

def main():
    opts = load_options()
    progress = load_progress()
    esphome_container = opts["esphome_container"]
    skip_offline = bool(opts["skip_offline"])
    delay = int(opts["delay_between_updates"])

    addr_map = read_address_map(esphome_container)

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

        name = dev["name"]
        yaml_name = dev["config"]
        if name in progress["done"]:
            continue

        log(""); log(f"[{idx}/{total}] Processing: {name}")
        log(f"Config: {yaml_name}")

        deployed,current = read_versions(esphome_container, yaml_name)
        log(f"Deployed: {deployed} | Current: {current}")

        # address preference: dashboard IP/host -> stem.local (later)
        addr = ""
        entry = addr_map.get(yaml_name)
        if entry:
            addr = (entry.get("address") or "").strip()
            if addr:
                log(f"Address (dashboard): {addr}")

        # ping ONLY if we have a numeric IP; skip ping for hostnames/mdns
        if skip_offline and addr and _is_ip(addr):
            if not ping_ip(addr):
                log(f"Device appears offline; skipping: {name}")
                if name not in progress["skipped"]:
                    progress["skipped"].append(name)
                save_progress(progress)
                continue
        elif skip_offline and addr and not _is_ip(addr):
            log("Non-numeric address (likely mDNS); skipping ping and proceeding to uploader.")

        log(f"Starting update for {name}")
        bin_path, esphome_name = compile_in_esphome_container(esphome_container, yaml_name, name)
        if STOP_REQUESTED:
            log("Stop requested during compile; saving progress and exiting.")
            break
        if not bin_path:
            if name not in progress["failed"]:
                progress["failed"].append(name)
            save_progress(progress)
            continue

        # Choose upload target: prefer dashboard address if present; else esphome_name.local; else stem.local
        if addr:
            target = addr
        elif esphome_name:
            target = f"{esphome_name}.local"
            log(f"No dashboard address; using mDNS target: {target}")
        else:
            target = f"{name}.local"
            log(f"No dashboard address or build name; using fallback: {target}")

        ok = upload_via_esphome(esphome_container, yaml_name, target)
        if ok:
            log(f"✓ Successfully updated {name}")
            if name in progress["failed"]:
                progress["failed"] = [x for x in progress["failed"] if x != name]
            if name not in progress["done"]:
                progress["done"].append(name)
        else:
            log(f"✗ Update failed for {name}")
            if name not in progress["failed"]:
                progress["failed"].append(name)

        save_progress(progress)

        for _ in range(max(0, delay)):
            if STOP_REQUESTED: break
            time.sleep(1)
        if STOP_REQUESTED:
            log("Stop requested after delay; saving progress and exiting.")
            break

    # Final dedupe + summary
    save_progress(progress)
    log(""); log("Summary:")
    log(f"  Done:   {len(progress['done'])}")
    log(f"  Failed: {len(progress['failed'])}")
    log(f"  Skipped:{len(progress['skipped'])}")
    log("All done.")

if __name__ == "__main__":
    main()