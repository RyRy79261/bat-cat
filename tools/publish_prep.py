#!/usr/bin/env python3
"""Build a store-publishable flattened tree for an app in dist/<app>/.

- vendors shared libs (release mode: DEBUG=False)
- copies the app folder minus dev-only files (metadata.json, caches)
- strips the [publish] section from tildagon.toml (mono-internal config)
- rewrites metadata.url to the target repo

The result is exactly what the target app repo's root should contain.

Usage: python tools/publish_prep.py <app> --repo owner/name
"""

import argparse
import shutil
import sys
from pathlib import Path

from vendor import vendor

ROOT = Path(__file__).resolve().parent.parent


def rewrite_manifest(text, repo_url):
    out = []
    section = ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped
        if section == "[publish]":
            continue
        if section == "[metadata]" and stripped.startswith("url"):
            line = f'url = "{repo_url}"'
        out.append(line)
    while out and not out[-1].strip():
        out.pop()
    return "\n".join(out) + "\n"


def prep(app, repo):
    app_dir = vendor(app, release=True)
    dist = ROOT / "dist" / app
    if dist.exists():
        shutil.rmtree(dist)
    shutil.copytree(
        app_dir,
        dist,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "metadata.json", ".pytest_cache"),
    )
    manifest = dist / "tildagon.toml"
    manifest.write_text(rewrite_manifest(manifest.read_text(), f"https://github.com/{repo}"))
    print(f"prepared {dist} for {repo}")
    return dist


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("app")
    parser.add_argument("--repo", required=True, help="target owner/name")
    args = parser.parse_args()
    if not (ROOT / "apps" / args.app).is_dir():
        sys.exit(f"no such app: {args.app}")
    prep(args.app, args.repo)
