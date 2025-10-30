#!/usr/bin/env python3
import json, os, re, signal, subprocess, sys, time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple, Dict

ADDON_OPTIONS_PATH = Path("/data/options.json")
STATE_PATH         = Path("/data/state.json")
LOG_FILE           = Path("/config/esphome_smart_update.log")
PROGRESS_FILE      = Path("/config/esphome_update_progress.json")

DEFAULTS = {
    "ota_password": "",
    "skip_offline": True,
    "delay_between_updates": 3,
    "esphome_container": "addon_15ef4d2f_esphome",
    "clear_log_now": False,
    "clear_progress_now": False,
    "always_clear_log_on_version_change": True,
}

STOP_REQUESTED = False
CURRENT_CHILD: Optional[subprocess.Popen] = None

def ts(): return datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")

def log(msg: str):
    line = f"{ts()} {msg}"
    print(line, flush=True)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f: f.write(line + "\n")
    except Exception: pass

def truncate_file(path: Path):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8"):
            pass
    except Exception as e:
        log(f"Warning: failed to truncate {path}: {e}")

def _sig_handler(signum, frame):
    global STOP_REQUESTED, CURRENT_CHILD
    STOP_REQUESTED = True
    if CURRENT_CHILD and CURRENT_CHILD.poll() is None:
        try: os.killpg(os.getpgid(CURRENT_CHILD.pid), signal.SIGTERM)
        except Exception:
            try: CURRENT_CHILD.terminate()
            except Exception: pass

signal.signal(signal.SIGTERM, _sig_handler)
signal.signal(signal.SIGINT, _sig_handler)

def load_json(path: Path, default):
    if path.exists():
        try: return json.loads(path.read_text(encoding="utf-8"))
        except Exception: return default
    return default

def save_json(path: Path, data: dict):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    except Exception as e:
        log(f"Warning: failed to write {path}: {e}")

def load_options() -> Dict:
    opts = DEFAULTS.copy()
    if ADDON_OPTIONS_PATH.exists():
        try:
            loaded = json.loads(ADDON_OPTIONS_PATH.read_text(encoding="utf-8"))
            for k in DEFAULTS:
                if k in loaded: opts[k] = loaded[k]
        except Exception as e:
            log(f"Warning: options.json parse error: {e}")
    return opts

def load_state() -> Dict:
    return load_json(STATE_PATH, {
        "last_version": None,
        "clear_log_now_consumed": False,
        "clear_progress_now_consumed": False
    })

def save_state(state: Dict): save_json(STATE_PATH, state)
def load_progress() -> Dict: return load_json(PROGRESS_FILE, {"done": [], "failed": [], "skipped": []})
def save_progress(data: dict): save_json(PROGRESS_FILE, data)

def ping_host(host: str) -> bool:
    for args in (["-c","1","-w","1"], ["-c","1","-W","1"]):
        try:
            rc = subprocess.run(["ping"] + args + [host], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
            if rc == 0: return True
        except FileNotFoundError:
            return True
        except Exception:
            pass
    return False

ESPHOME_NAME_RE = re.compile(r"^esphome:\s*$", re.MULTILINE)
NAME_LINE_RE    = re.compile(r"^\s{name}\s*:\s*(\S+)\s*$".format(name="name"))

def parse_node_name(yaml_text: str) -> Optional[str]:
    """Minimal parser: find 'esphome:' block, then the first indented 'name: <value>'."""
    m = ESPHOME_NAME_RE.search(yaml_text)
    if not m:  # also support top-level 'name:' seen in older configs (last resort)
        m2 = re.search(r"^\s*name\s*:\s*([^\s#]+)", yaml_text, re.MULTILINE)
        return m2.group(1).strip() if m2 else None
    start = m.end()
    # take following indented lines until next top-level key
    block = []
    for line in yaml_text[start:].splitlines():
        if line.strip() == "": block.append(line); continue
        if not line.startswith(" "): break  # next top-level section
        block.append(line)
    for line in block:
        m2 = NAME_LINE_RE.match(line)
        if m2:
            return m2.group(1).strip()
    return None

def discover_devices() -> List[dict]:
    esphome_dir = Path("/config/esphome")
    out = []
    for y in sorted(esphome_dir.glob("*.yaml")):
        try: text = y.read_text(encoding="utf-8", errors="ignore")
        except Exception: text = ""
        ip  = None
        m_ip = re.search(r"manual_ip\s*:\s*([0-9]{1,3}(?:\.[0-9]{1,3}){3})", text)
        if m_ip: ip = m_ip.group(1).strip()
        node = parse_node_name(text) or y.stem  # fallback to stem if not found
        out.append({
            "name": y.stem,          # file base (ai001, as007, …)
            "node": node,            # real ESPHome node name (ai001-lounge-…, as007-shop-…, …)
            "config": y.name,
            "address": ip,
        })
    return out

def _run(cmd: list[str], env: Optional[dict]=None, capture: bool=False, text_out: bool=True) -> Tuple[int, str]:
    global CURRENT_CHILD
    if STOP_REQUESTED: return (143, "")
    try:
        if capture:
            p = subprocess.Popen(cmd, env=env, preexec_fn=os.setsid, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=text_out)
        else:
            p = subprocess.Popen(cmd, env=env, preexec_fn=os.setsid)
        CURRENT_CHILD = p
        out = ""
        if capture:
            out = p.communicate()[0] or ""
            rc = p.returncode
        else:
            rc = p.wait()
        return (rc, out)
    finally:
        CURRENT_CHILD = None

def docker_exec(container: str, args: list[str], capture: bool=False) -> Tuple[int, str]:
    return _run(["docker","exec",container] + args, os.environ.copy(), capture=capture)

def docker_cp(src_container: str, src_path: str, dst_path: str) -> int:
    rc, _ = _run(["docker","cp", f"{src_container}:{src_path}", dst_path], os.environ.copy(), capture=False)
    return rc

def get_current_esphome_version(container: str) -> str:
    rc, out = docker_exec(container, ["esphome","version"], capture=True)
    if rc == 0:
        m = re.search(r"ESPHome\s+([0-9][^\s]*)", out)
        if m: return m.group(1).strip()
    return "unknown"

def read_versions(current_core_version: str, device_name: str, progress: Dict) -> Tuple[str,str]:
    deployed = current_core_version if device_name in progress.get("done", []) else "unknown"
    return (deployed, current_core_version)

def compile_in_esphome_container(container: str, yaml_name: str, device_name: str) -> Optional[str]:
    log(f"→ Compiling {yaml_name} via docker in '{container}'")
    rc, _ = docker_exec(container, ["esphome","compile", f"/config/esphome/{yaml_name}"], capture=False)
    if rc != 0 or STOP_REQUESTED:
        if STOP_REQUESTED: log("Stop requested; aborting compile.")
        else: log(f"✗ Compilation failed for {device_name}")
        return None

    stem    = Path(yaml_name).stem
    pio_bin = f"/data/build/{stem}*/.pioenvs/{stem}*/firmware.bin"
    legacy  = f"/config/esphome/.esphome/build/{stem}/{stem}.bin"
    dst_dir = Path("/config/esphome/builds"); dst_dir.mkdir(parents=True, exist_ok=True)
    dst     = str(dst_dir / f"{stem}.bin")

    rc, out = docker_exec(container, ["sh","-lc", f"set -e; ls -1 {pio_bin} 2>/dev/null | head -n1"], capture=True)
    if rc == 0 and out.strip():
        src = out.strip().splitlines()[0].strip()
        if docker_cp(container, src, dst) == 0:
            log(f"→ Binary copied to {dst} (from {src})")
            return dst

    if docker_cp(container, legacy, dst) == 0:
        log(f"→ Binary copied to {dst} (from {legacy})")
        return dst

    log(f"✗ Could not locate firmware binary for {device_name} (checked new/old paths and *.bin glob)")
    return None

def ota_upload_via_esphome(container: str, yaml_name: str, target: str) -> Tuple[bool, str]:
    args = ["esphome","upload", f"/config/esphome/{yaml_name}", "--device", target]
    rc, out = docker_exec(container, args, capture=True)
    return (rc == 0 or ("OTA successful" in out) or ("Successfully uploaded program" in out), out)

def main():
    opts    = load_options()
    state   = load_state()
    progress= load_progress()

    esphome_container = opts["esphome_container"]
    skip_offline      = bool(opts["skip_offline"])
    delay             = int(opts["delay_between_updates"])

    # housekeeping
    addon_version = os.environ.get("ADDON_VERSION", "unknown")
    if opts.get("always_clear_log_on_version_change", True):
        if addon_version and addon_version != state.get("last_version"):
            truncate_file(LOG_FILE)
            log(f"Add-on version changed: {state.get('last_version')} → {addon_version}. Log cleared.")
            state["last_version"] = addon_version
            save_state(state)

    if bool(opts.get("clear_log_now", False)) and not state.get("clear_log_now_consumed", False):
        truncate_file(LOG_FILE); log("Log cleared by user request (clear_log_now).")
        state["clear_log_now_consumed"] = True; save_state(state)
    elif not bool(opts.get("clear_log_now", False)) and state.get("clear_log_now_consumed", False):
        state["clear_log_now_consumed"] = False; save_state(state)

    if bool(opts.get("clear_progress_now", False)) and not state.get("clear_progress_now_consumed", False):
        truncate_file(PROGRESS_FILE); progress = {"done": [], "failed": [], "skipped": []}; save_progress(progress)
        log("Progress cleared by user request (clear_progress_now).")
        state["clear_progress_now_consumed"] = True; save_state(state)
    elif not bool(opts.get("clear_progress_now", False)) and state.get("clear_progress_now_consumed", False):
        state["clear_progress_now_consumed"] = False; save_state(state)

    log("="*79); log("ESPHome Smart Updater (Docker exec mode)"); log("="*79)
    current_core_version = get_current_esphome_version(esphome_container)

    devices = discover_devices()
    total   = len(devices)
    log(f"Found {total} total devices to consider")

    done    = set(progress.get("done", []))
    failed  = set(progress.get("failed", []))
    skipped = set(progress.get("skipped", []))

    for idx, dev in enumerate(devices, start=1):
        if STOP_REQUESTED: log("Stop requested; saving progress and exiting."); break

        name      = dev["name"]    # file stem
        node      = dev["node"]    # real node name
        yaml_name = dev["config"]
        ip        = dev["address"]

        if name in done: continue

        log(""); log(f"[{idx}/{total}] Processing: {name}")
        log(f"Config: {yaml_name}")

        deployed, current = read_versions(current_core_version, name, progress)
        log(f"Deployed: {deployed} | Current: {current}")

        # decide target
        target = ip if ip else f"{node}.local"
        if not ip:
            log(f"No dashboard address; using mDNS target: {target}")

        # optional ping only if we have IP
        if skip_offline and ip and not ping_host(ip):
            log(f"Device appears offline; skipping: {name}")
            skipped.add(name); progress["skipped"] = sorted(list(skipped)); save_progress(progress); continue

        log(f"Starting update for {name}")
        bin_path = compile_in_esphome_container(esphome_container, yaml_name, name)
        if STOP_REQUESTED: log("Stop requested during compile; saving progress and exiting."); break
        if not bin_path:
            failed.add(name); progress["failed"] = sorted(list(failed)); save_progress(progress); continue

        ok, out = ota_upload_via_esphome(esphome_container, yaml_name, target)
        if ok:
            log("→ OTA upload reported success.")
            done.add(name); failed.discard(name)
            progress["done"] = sorted(list(done)); progress["failed"] = sorted(list(failed)); save_progress(progress)
        else:
            tail = "\n".join(out.splitlines()[-40:])
            log("OTA uploader output (tail):"); 
            for line in tail.splitlines(): log(f"  {line}")
            log(f"✗ Update failed for {name}")
            failed.add(name); progress["failed"] = sorted(list(failed)); save_progress(progress)

        for _ in range(max(0, delay)):
            if STOP_REQUESTED: break
            time.sleep(1)
        if STOP_REQUESTED: log("Stop requested after delay; saving progress and exiting."); break

    log(""); log("Summary:")
    log(f"  Done:   {len(done)}"); log(f"  Failed: {len(failed)}"); log(f"  Skipped:{len(skipped)}")
    log("All done.")
    progress["done"]    = sorted(list(done))
    progress["failed"]  = sorted(list(failed))
    progress["skipped"] = sorted(list(skipped))
    save_progress(progress)

if __name__ == "__main__":
    main()