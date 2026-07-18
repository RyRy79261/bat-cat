#!/usr/bin/env python3
"""Decide which apps to publish; emits a GitHub Actions matrix.

workflow_dispatch: publish exactly the requested app (first publish or update).
push to main:      auto-update every publishable app whose manifest version has
                   no matching release yet.

Two publishing modes, chosen per app by where its target repo points:

same-repo (target == this repo): the flattened app is pushed to this repo's
    `store` branch and the release targets that branch. Works with the built-in
    GITHUB_TOKEN, and first publishes are automatic — the repo obviously exists.

mirror (target is another repo): the app is pushed to that repo's `main`.
    Needs a PUBLISH_TOKEN PAT; first publishes stay manual (the target repo
    must exist and already have a release before auto-updates kick in).

Target repo resolution: --repo input > [publish].repo in tildagon.toml >
<owner>/spaceagon-<app-with-dashes>.

Env: EVENT_NAME, INPUT_APP, INPUT_REPO, OWNER, GITHUB_REPOSITORY, GH_TOKEN,
GITHUB_OUTPUT.
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
    try:
        result = subprocess.run(["gh", "api", *args], capture_output=True, text=True)
    except FileNotFoundError:
        sys.exit("gh CLI not found — publish planning needs it")
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)


def latest_release_tag(repo):
    data = gh_json(f"repos/{repo}/releases/latest")
    return data.get("tag_name") if data else None


def main():
    event = os.environ.get("EVENT_NAME", "")
    this_repo = os.environ.get("GITHUB_REPOSITORY", "")
    entries = []

    def entry(app, repo, version):
        branch = "store" if repo == this_repo else "main"
        return {"app": app, "repo": repo, "version": version, "branch": branch}

    if event == "workflow_dispatch":
        app = os.environ["INPUT_APP"].strip()
        if not (ROOT / "apps" / app).is_dir():
            sys.exit(f"no such app: {app}")
        data = load(app)
        repo = target_repo(app, data, os.environ.get("INPUT_REPO", "").strip() or None)
        entries.append(entry(app, repo, data["metadata"]["version"]))
    elif not os.environ.get("GH_TOKEN"):
        print("no GH_TOKEN — skipping auto-update scan")
    else:
        for manifest in sorted(ROOT.glob("apps/*/tildagon.toml")):
            app = manifest.parent.name
            data = load(app)
            repo = target_repo(app, data)
            version = data["metadata"]["version"]
            if gh_json(f"repos/{repo}/releases/tags/v{version}") is not None:
                print(f"skip {app}: v{version} already released")
                continue
            if repo != this_repo:
                if gh_json(f"repos/{repo}") is None:
                    print(f"skip {app}: {repo} does not exist (not yet published)")
                    continue
                if latest_release_tag(repo) is None:
                    print(f"skip {app}: {repo} has no releases (first publish is manual)")
                    continue
            entries.append(entry(app, repo, version))

    print("matrix:", json.dumps(entries, indent=2))
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as handle:
            handle.write(f"matrix={json.dumps(entries)}\n")


if __name__ == "__main__":
    main()
