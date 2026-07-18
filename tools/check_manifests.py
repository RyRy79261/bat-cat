#!/usr/bin/env python3
"""Sanity-check every apps/*/tildagon.toml against the app-store rules that
matter (required fields, category enum, docs' length limits, version format).

Full zod-schema validation only matters for store publishing, which is out of
scope for this template — these checks keep manifests honest anyway.
"""

import sys
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parent.parent
CATEGORIES = {"Badge", "Music", "Media", "Apps", "Games", "Background", "Pattern"}
REQUIRED_META = ("author", "license", "url", "description", "version")


def check(path):
    errors = []
    data = tomllib.loads(path.read_text())
    app = data.get("app", {})
    meta = data.get("metadata", {})
    if not app.get("name"):
        errors.append("app.name missing")
    cats = app.get("category")
    cats = cats if isinstance(cats, list) else [cats]
    for cat in cats:
        if cat not in CATEGORIES:
            errors.append(f"app.category {cat!r} not in {sorted(CATEGORIES)}")
    for key in REQUIRED_META:
        if not isinstance(meta.get(key), str) or not meta.get(key):
            errors.append(f"metadata.{key} missing or not a string")
    if isinstance(meta.get("author"), str) and len(meta["author"]) > 32:
        errors.append("metadata.author over 32 chars")
    if isinstance(meta.get("description"), str) and len(meta["description"]) > 140:
        errors.append("metadata.description over 140 chars")
    version = meta.get("version", "")
    if isinstance(version, str) and version:
        parts = version.split(".")
        widths = {len(p) for p in parts[1:]}
        if not all(p.isdigit() for p in parts):
            errors.append(f"version {version!r} has non-numeric components")
        elif len(widths) > 1:
            # badge update check compares version components as STRINGS —
            # keep component widths fixed (e.g. 1.00.00) or 0.9 -> 0.10 breaks
            errors.append(f"version {version!r} components should be fixed-width")
    return errors


def main():
    manifests = sorted(ROOT.glob("apps/*/tildagon.toml"))
    if not manifests:
        sys.exit("no apps/*/tildagon.toml found")
    failed = False
    for path in manifests:
        errors = check(path)
        rel = path.relative_to(ROOT)
        if errors:
            failed = True
            print(f"FAIL {rel}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"ok   {rel}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
