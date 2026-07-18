#!/usr/bin/env python3
"""Sideload an app onto a badge over USB (plug into the USB *IN* port).

Vendors shared libs first, then copies the whole app folder to /apps/<app>/
with mpremote. Hold the "reboop" button ~2s afterwards to restart the badge.

Usage: python tools/deploy.py <app>
"""

import argparse
import subprocess
import sys

from vendor import vendor


def run(cmd, check=True):
    print("+", " ".join(cmd))
    return subprocess.run(cmd, check=check)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("app")
    args = parser.parse_args()
    app_dir = vendor(args.app)

    run(["mpremote", "mkdir", ":/apps"], check=False)  # may already exist
    run(["mpremote", "rm", "-r", f":/apps/{args.app}"], check=False)
    result = run(["mpremote", "fs", "cp", "-r", str(app_dir), ":/apps/"], check=False)
    if result.returncode != 0:
        sys.exit(
            "mpremote copy failed. Is the badge plugged into the USB IN port?\n"
            "Install mpremote with: uv tool install mpremote  (or pip install mpremote)"
        )
    print(f"\nDeployed. Hold the reboop button ~2s to restart, then launch '{args.app}'.")


if __name__ == "__main__":
    main()
