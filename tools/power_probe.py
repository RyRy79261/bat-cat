#!/usr/bin/env python3
"""A/B power probe: run an app in the official simulator, headless, under
different sensor/redraw throttle configs, and compare hardware-access rates
plus host CPU time (the closest off-badge proxy for battery draw — the sim
has no battery model, but I2C transactions and full-screen repaints are the
power costs on the badge, and both are counted here).

Each run gets an identical scripted tilt stimulus (idle -> active -> idle)
injected by the app's probe module, so the configs are directly comparable.

Usage: python3.10 tools/power_probe.py cat_yarn [--seconds 60] [--config NAME]
Requires the same setup as tools/sim.py (Python 3.10 + pygame/wasmtime).
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from sim import class_name, firmware_dir
from vendor import vendor

ROOT = Path(__file__).resolve().parent.parent

# One flag namespace per app; sim settings.json is flat and shared.
FLAG_PREFIX = "spmono_catyarn_"

CONFIGS = {
    # Pre-throttle behaviour: IMU read + repaint on every ~50 ms tick.
    "baseline": {"imu_ms": 0, "imu_idle_ms": 0, "draw_ms": 0},
    # The proposed defaults: 10 Hz IMU (2.5 Hz idle), ~12.5 fps repaint cap.
    "throttled": {"imu_ms": 100, "imu_idle_ms": 400, "draw_ms": 80},
    # Baseline rates with the battery monitor effectively off (one read at
    # boot, never again) — isolates the monitor's own contribution.
    "no_battery": {"imu_ms": 0, "imu_idle_ms": 0, "draw_ms": 0, "battery_ms": 1 << 30},
}

# idle -> active -> idle stimulus window (seconds into the run).
WIGGLE = (10.0, 40.0)


def proc_cpu_seconds(pid):
    # utime + stime from /proc, covers all threads of the process.
    with open(f"/proc/{pid}/stat") as f:
        fields = f.read().rsplit(") ", 1)[1].split()
    ticks = int(fields[11]) + int(fields[12])
    return ticks / os.sysconf("SC_CLK_TCK")


def run_config(app, sim_dir, fw_root, name, flags, seconds):
    settings_path = fw_root / "settings.json"
    stats_path = ROOT / ".cache" / "probe" / f"{name}.json"
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    if stats_path.exists():
        stats_path.unlink()

    merged = {FLAG_PREFIX + "debug_overlay": False}
    for key, value in flags.items():
        merged[FLAG_PREFIX + key] = value
    settings_path.write_text(json.dumps(merged))

    env = dict(os.environ)
    env["CATYARN_PROBE"] = str(stats_path)
    env["CATYARN_PROBE_WIGGLE"] = f"{WIGGLE[0]}:{WIGGLE[1]}"
    env.setdefault("SDL_VIDEODRIVER", "dummy")
    env.setdefault("SDL_AUDIODRIVER", "dummy")

    cmd = [sys.executable, "run.py", f"{app}.{class_name(app)}"]
    print(f"[{name}] {' '.join(cmd)} for {seconds}s ...")
    proc = subprocess.Popen(
        cmd,
        cwd=sim_dir,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(seconds)
        cpu_s = proc_cpu_seconds(proc.pid)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

    if not stats_path.exists():
        sys.exit(f"[{name}] no stats written — did the app crash? Re-run tools/sim.py {app}")
    stats = json.loads(stats_path.read_text())
    stats["cpu_s"] = cpu_s
    stats["wall_s"] = seconds
    return stats


def report(results, seconds):
    rows = [
        ("imu reads/min", "imu_reads"),
        ("battery reads/min", "battery_level_reads"),
        ("draws/min", "draws"),
        ("updates/min", "updates"),
        ("idle updates/min", "idle_updates"),
    ]
    names = list(results)
    width = max(len(label) for label, _ in rows) + 2
    print()
    print(" " * width + "".join(f"{n:>14}" for n in names))
    for label, key in rows:
        cells = "".join(f"{results[n][key] * 60.0 / results[n]['elapsed_s']:>14.1f}" for n in names)
        print(f"{label:<{width}}{cells}")
    cells = "".join(f"{results[n]['cpu_s']:>14.2f}" for n in names)
    print(f"{'host CPU s / run':<{width}}{cells}")
    if "baseline" in results:
        base_cpu = results["baseline"]["cpu_s"]
        cells = "".join(f"{100.0 * (1.0 - results[n]['cpu_s'] / base_cpu):>13.1f}%" for n in names)
        print(f"{'CPU vs baseline':<{width}}{cells}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("app")
    parser.add_argument("--seconds", type=float, default=60.0)
    parser.add_argument("--config", action="append", choices=sorted(CONFIGS), default=None)
    args = parser.parse_args()

    app_dir = vendor(args.app)
    fw_root = firmware_dir()
    sim_dir = fw_root / "sim"
    target = sim_dir / "apps" / args.app
    if target.is_symlink() or target.exists():
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        else:
            target.unlink()
    try:
        target.symlink_to(app_dir, target_is_directory=True)
    except OSError:
        shutil.copytree(app_dir, target)

    settings_path = fw_root / "settings.json"
    saved = settings_path.read_text() if settings_path.exists() else None
    results = {}
    try:
        for name in args.config or list(CONFIGS):
            results[name] = run_config(
                args.app, sim_dir, fw_root, name, CONFIGS[name], args.seconds
            )
    finally:
        if saved is None:
            if settings_path.exists():
                settings_path.unlink()
        else:
            settings_path.write_text(saved)

    out = ROOT / ".cache" / "probe" / "results.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"\nwrote {out}")
    report(results, args.seconds)


if __name__ == "__main__":
    main()
