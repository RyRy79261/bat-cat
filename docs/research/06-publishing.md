# Publishing, the app store, and the monorepo problem

> Research snapshot: 2026-07-18. Verified against the actual app-store backend source
> (`emfcamp/badge-2024-app-store` @ `299f7f7`, 2026-07-14) and the on-badge installer
> (`modules/firmware_apps/app_store.py` in the firmware repo).

## How publishing works (fully automated, no review)

An app is published by having a **GitHub or Codeberg repository** with:

1. `app.py` at the **repo root**, defining `__app_export__`
2. `tildagon.toml` (or `tildagon.json` — but not both) at the **repo root**
3. at least one **release** (e.g. tag `v0.0.1`)
4. the **`tildagon-app` topic** on the repo

The store scans GitHub (GraphQL: `topic:tildagon-app fork:true archived:false`) roughly
every 10 minutes ("within 15 minutes" per docs), ingests **only the latest release** per
repo, and serves the release's **whole-repo tarball** (cached at
`apps.badge.emfcamp.org/v1/tarballs/...`). App identity = `md5(service+owner+repoName)` →
an 8-character app code; each app gets `https://apps.badge.emfcamp.org/apps/<app-id>/`.
Ingestion failures show at <https://apps.badge.emfcamp.org/errors/>. Moderation is a
reactive blocklist; there is no human review and no published UX rules (conventions only).

Updates: bump `version` in the manifest **and create a new release**. ⚠ On-badge update
detection compares versions with a lexicographic per-component list compare
(`"0.9" > "0.10"` — so a 0.9→0.10 bump is NOT detected). Keep components single-digit or
zero-pad.

`.gitattributes` `export-ignore` lines keep files (README, images, dev scripts) out of the
release tarball users download.

## tildagon.toml — the schema

Store-validated fields (zod schema in `packages/tildagon-app/src/TildagonAppManifest.ts`):

```toml
[app]
name = "My App"                      # required
category = "Apps"                    # required; string or array from:
                                     # Badge, Music, Media, Apps, Games, Background, Pattern

[entry]
# class = "MyApp"                    # NOT validated by store; badge uses __app_export__

[metadata]
author = "your-name"                 # required (≤32 chars per docs)
license = "MIT"                      # required, SPDX id
url = "https://github.com/you/repo"  # required
description = "..."                  # required (≤140 chars per docs)
version = "0.0.1"                    # required, string

# Optional 2026 capability metadata (store filters on these):
# [[metadata.capabilities]]
# required = true
# feature = { type = "2026 Frontboard" }          # or "2024 Frontboard"
# [[metadata.capabilities]]
# required = false
# feature = { type = "TildagonOSMinimumVersion", version = "2.0.0" }
# feature can also be a hexpansion: { vid = 0x1234, pid = 0x5678, name = "..." }
# or { type = "Capability", identifier = "https://..." }
```

⚠ **Known firmware bug**: the store schema spells the feature `"TildagonOSMinimumVersion"`
but the on-badge checker (`system/capabilities/utils.py`) compares against
`"TildagonOsMinimumVersion"` (lowercase "s") — so a store-valid minimum-OS requirement is
**silently ignored on-badge**. Declare it for store filtering if you like, but always guard
OS-version-sensitive features at runtime yourself.

`menu` and `wifi_preference` are legal extras the badge reads but the store ignores.

## ⚠ THE monorepo verdict: the store requires one-repo-per-app

Confirmed from the ingestion source code, not just docs:

- Manifest is fetched at the **fixed root path** `tildagon.toml`/`tildagon.json` — no
  subdirectory configuration exists.
- Only `releases(first: 1)` per repo — even per-app tags in one repo would surface one app.
- App identity hashes `service+owner+repoName` — **no path component** in the identity model.
- The on-badge installer requires the tarball to contain **exactly one root directory** with
  `app.py`/`app.mpy` **directly inside it** — a monorepo tarball fails install regardless.

**What DOES work in one published repo:** extra directories *alongside* the root `app.py`
ship fine and are fully extracted (vendored libraries, assets, even a server + tests —
see `area/racecondition`). So each *published* artifact is "one app at repo root + anything
else", not "many apps".

### Our strategy: this repo IS the store repo (via a `store` branch)

The store's constraints bind the **release tarball**, not the default branch: it ingests
the latest release, and a release can target any branch. So `bat-cat` publishes itself —
`main` stays a monorepo, and `publish.yml` maintains a store-shaped `store` branch:

```
bat-cat (this repo — store identity RyRy79261/bat-cat, store name "bat-cat")
  main:  apps/cat_yarn/   app.py, tildagon.toml (source of truth)
         libs/spmono/     shared code, vendored INTO the app at release time
        │
        ▼  publish.yml: flatten (vendor libs, DEBUG=False, strip dev files)
  store branch: root app.py + tildagon.toml   (force-pushed, generated)
        │
        ▼  release v<version> --target store  (built-in GITHUB_TOKEN; no PAT)
apps.badge.emfcamp.org → badge App Store client  (topic `tildagon-app` set by hand once)
```

Because only the **latest release** per repo is ingested, this repo can publish exactly
one app. A second app would need a **mirror repo** (the classic monorepo workaround:
copy the flattened app to its own repo + topic + release) — `publish.yml` retains that
mode behind a `PUBLISH_TOKEN` PAT. Sideloading has **no** layout constraints — the
monorepo works as-is for development and manual distribution.

## Install / size / shared code realities

- The badge App Store client downloads the tarball and gzip-decompresses **entirely in RAM**;
  there's no explicit size limit — `MemoryError` = "Out of memory (app too big?)". Keep
  tarballs lean (export-ignore) — remember: 2 MB PSRAM total.
- Apps install to `/apps/<owner>_<repo>/` and are imported as the package
  `apps.<owner>_<repo>` — **use package-relative imports** inside an app.
- **No cross-app dependency mechanism exists.** No shared-library install, no pip/mip flow.
  Each app **vendors** everything beyond firmware built-ins. (One installed app *could*
  import another's package by path, but nothing guarantees it's installed — don't.)
- Also installable on-badge by 8-digit code ("Use Code" — e.g. `21230442` is the official
  Spaceagon test app).

## Key sources

- <https://tildagon.badge.emfcamp.org/tildagon-apps/publish/>
- <https://github.com/emfcamp/badge-2024-app-store> — esp.
  `packages/tildagon-app-directory-api/src/registries/sources/github.ts` (ingestion),
  `packages/tildagon-app/src/TildagonAppManifest.ts` (schema),
  `packages/tildagon-app/src/TildagonAppRelease.ts` (identity)
- `modules/firmware_apps/app_store.py` in <https://github.com/emfcamp/badge-2024-software>
  (installer, updater, version compare)
- Template repo the docs tell you to fork: <https://github.com/hughrawlinson/tildagon-demo>
