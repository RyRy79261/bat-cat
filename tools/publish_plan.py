#!/usr/bin/env python3
"""Decide which apps to publish; emits a GitHub Actions matrix.

workflow_dispatch: publish exactly the requested app (first publish or update).
push to main:      auto-update every app that is ALREADY published (target repo
                   exists and has a release) whose manifest version has no
                   matching release yet. First publishes stay manual.

Target repo resolution: --repo input > [publish].repo in tildagon.toml >
<owner>/spaceagon-<app-with-dashes>.

Env: EVENT_NAME, INPUT_APP, INPUT_REPO, OWNER, GH_TOKEN, GITHUB_OUTPUT.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parent.parent


def load(app):
    return tomllib.loads((ROOT / "apps" / app / "tildagon.toml").read_text())


def target_repo(app, data, override=None):
    return (
        override
        or data.get("publish", {}).get("repo")
        or f"{os.environ['OWNER']}/spaceagon-{app.replace('_', '-')}"
    )


def gh_json(*args):
    result = subprocess.run(["gh", "api", *args], capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)


def latest_release_tag(repo):
    data = gh_json(f"repos/{repo}/releases/latest")
    return data.get("tag_name") if data else None


def main():
    event = os.environ.get("EVENT_NAME", "")
    entries = []

    if event == "workflow_dispatch":
        app = os.environ["INPUT_APP"].strip()
        if not (ROOT / "apps" / app).is_dir():
            sys.exit(f"no such app: {app}")
        data = load(app)
        repo = target_repo(app, data, os.environ.get("INPUT_REPO", "").strip() or None)
        entries.append({"app": app, "repo": repo, "version": data["metadata"]["version"]})
    else:
        if not os.environ.get("GH_TOKEN"):
            print("PUBLISH_TOKEN secret not set — skipping auto-update scan")
        else:
            for manifest in sorted(ROOT.glob("apps/*/tildagon.toml")):
                app = manifest.parent.name
                data = load(app)
                repo = target_repo(app, data)
                if gh_json(f"repos/{repo}") is None:
                    print(f"skip {app}: {repo} does not exist (not yet published)")
                    continue
                tag = latest_release_tag(repo)
                if tag is None:
                    print(f"skip {app}: {repo} has no releases (first publish is manual)")
                    continue
                version = data["metadata"]["version"]
                if tag == f"v{version}":
                    print(f"skip {app}: v{version} already released")
                    continue
                entries.append({"app": app, "repo": repo, "version": version})

    print("matrix:", json.dumps(entries, indent=2))
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as handle:
            handle.write(f"matrix={json.dumps(entries)}\n")


if __name__ == "__main__":
    main()
