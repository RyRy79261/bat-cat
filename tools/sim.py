#!/usr/bin/env python3
"""Run an app in the official Tildagon simulator (desktop, CPython + pygame).

Requires Python 3.10 (the sim's pin). Set TILDAGON_FW to an existing
badge-2024-software checkout, or this script clones one into .cache/.

Simulates: display, the six buttons (keys a-f), LED ring, tilt via WASD.
Does NOT simulate 2026 inputs (joystick/touch/prox) or the compass — the sim
always boots as a 2024 board. Test those on real hardware.

Usage: python tools/sim.py cat_yarn [--screenshot]
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from vendor import vendor

ROOT = Path(__file__).resolve().parent.parent
FW_TAG = "v2.1.1"


def firmware_dir():
    env = os.environ.get("TILDAGON_FW")
    if env:
        return Path(env)
    cache = ROOT / ".cache" / "badge-2024-software"
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--branch",
                FW_TAG,
                "https://github.com/emfcamp/badge-2024-software",
                str(cache),
            ],
            check=True,
        )
    return cache


def class_name(app):
    # cat_yarn -> CatYarnApp (convention used by our app template)
    return "".join(part.capitalize() for part in app.split("_")) + "App"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("app")
    parser.add_argument("--screenshot", action="store_true")
    args = parser.parse_args()

    app_dir = vendor(args.app)
    fw = firmware_dir()
    sim_dir = fw / "sim"
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

    cmd = [sys.executable, "run.py"]
    if args.screenshot:
        cmd.append("--screenshot")
    cmd.append(f"{args.app}.{class_name(args.app)}")
    env = dict(os.environ)
    if args.screenshot:
        env.setdefault("SDL_VIDEODRIVER", "dummy")
        env.setdefault("SDL_AUDIODRIVER", "dummy")
    print("+", " ".join(cmd), f"(cwd={sim_dir})")
    sys.exit(subprocess.run(cmd, cwd=sim_dir, env=env).returncode)


if __name__ == "__main__":
    main()
