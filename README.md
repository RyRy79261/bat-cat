# spaceagon-mono

A monorepo of apps for the **EMF Camp Spaceagon badge** (the 2026 front-board upgrade of
the hexagonal Tildagon badge), plus shared libraries — notably a generic input-abstraction
layer for assigning functionality to buttons/joystick/touch and composing apps from reusable
parts.

> **Status: scaffold + example app built.** This repo is intended to be used as a
> GitHub **template repository** ("Use this template" → your own badge-app monorepo).

## Quick start

```sh
uv run pytest -q                      # unit tests (physics, cat brain, input, theme, flags)
uv run python tools/gen_cat_sprites.py  # regenerate sprite assets
just sim cat_yarn                     # run in the official simulator (needs Python 3.10;
                                      #   WASD = tilt, keys a-f = buttons)
just deploy cat_yarn                  # sideload to a badge over USB (USB IN port),
                                      #   then hold "reboop" ~2s to restart
```

## Layout

```
apps/cat_yarn/    Cat & Yarn — ambient toy: cats chase a tilt-driven yarn ball;
                  the screen rim is a battery-level "floor" ring. Reference app.
libs/spmono/      shared libs, vendored into each app by tools/vendor.py:
                  engine (physics/sprites/state machines), input (action maps,
                  edge/long-press detection), theme, flags, sensors, ui (BaseApp)
tools/            vendor.py, deploy.py, sim.py, gen_cat_sprites.py, check_manifests.py
tests/            CPython unit tests — no badge or simulator needed
docs/             research + proposals (see table below)
```

Design constraints baked in: MicroPython 1.28 compatibility (no `match`, no
dataclasses), one input vocabulary across 2024/2026 badges, apps stay
store-shaped (root `app.py` + `tildagon.toml`) so publishing is mechanical,
and pure-logic modules import no firmware so they test on plain CPython.

## Publishing to the Tildagon app store

The store requires one repo per app (root `app.py` + `tildagon.toml`, the
`tildagon-app` topic, and a GitHub Release). The **Publish apps** workflow
handles that from this monorepo:

1. **One-time per app:** create the empty target repo (default
   `<owner>/spaceagon-<app-dashes>`, or set `[publish] repo = "owner/name"` in
   the app's `tildagon.toml`), and add a `PUBLISH_TOKEN` repo secret — a
   fine-grained PAT with *Contents: read/write* on the target repos (plus
   *Administration: write* if you want the workflow to set the `tildagon-app`
   topic; otherwise add the topic by hand once).
2. **First publish:** Actions → *Publish apps to the Tildagon store* → Run
   workflow → app name. It flattens the app (vendored libs, `DEBUG=False`,
   dev `metadata.json` stripped, `[publish]` section removed, `metadata.url`
   rewritten), force-pushes it to the target repo, ensures the topic, and
   creates release `v<version>`. The store lists it within ~15 minutes
   (failures: <https://apps.badge.emfcamp.org/errors/>).
3. **Updates:** bump `version` in the app's `tildagon.toml` (keep components
   fixed-width — `1.00.00 → 1.00.01`; the badge compares version strings
   lexicographically) and merge to `main`. The workflow auto-releases every
   already-published app whose version has no matching release. Apps never
   published (no target repo / no release) are never auto-published.

## What is this badge?

- Hexagonal ESP32-S3 badge running **Tildagon OS** (MicroPython 1.28). Apps are plain
  Python — subclass `App`, implement `update(delta)` / `draw(ctx)`, export `__app_export__`.
- The 2026 **Spaceagon** front board adds: 6 buttons (A–F), a 5-way joystick, a 12-pad
  capacitive touch ring, 2 proximity sensors, and a compass — all on top of the 2024 base
  board (round 240×240 display, 18 usable RGB LEDs, IMU, WiFi/BLE/ESP-NOW, dual USB-C).
- Apps publish to the [official app directory](https://apps.badge.emfcamp.org/) via GitHub
  repos with the `tildagon-app` topic (one repo per app — see the publishing research for
  how this monorepo deals with that).

## Research docs (start here)

| Doc | Contents |
|---|---|
| [docs/PROPOSAL.md](docs/PROPOSAL.md) | Proposed architecture & stack (decision doc) |
| [docs/PROPOSAL-2-template-devkit-cat-app.md](docs/PROPOSAL-2-template-devkit-cat-app.md) | **Template repo, dev kit, CI/CD, theming, flags + the Cat & Yarn example app** |
| [docs/research/09-cat-app-feasibility.md](docs/research/09-cat-app-feasibility.md) | Feasibility research behind Proposal 2 |
| [docs/research/01-hardware.md](docs/research/01-hardware.md) | The hardware, chip by chip |
| [docs/research/02-app-model.md](docs/research/02-app-model.md) | How apps are written (App class, ctx, UI, eventbus) |
| [docs/research/03-input.md](docs/research/03-input.md) | Buttons/joystick/touch — full input API |
| [docs/research/04-sensors-and-peripherals.md](docs/research/04-sensors-and-peripherals.md) | IMU, compass, LEDs, power, radio |
| [docs/research/05-toolchain.md](docs/research/05-toolchain.md) | Simulate, sideload, debug, flash |
| [docs/research/06-publishing.md](docs/research/06-publishing.md) | App store mechanics + the monorepo verdict |
| [docs/research/07-ecosystem.md](docs/research/07-ecosystem.md) | Repos to learn from, community channels |
| [docs/research/08-verification-log.md](docs/research/08-verification-log.md) | How claims were adversarially verified + tooling recency audit |

## Upstream links

- Docs: <https://tildagon.badge.emfcamp.org/> · App directory: <https://apps.badge.emfcamp.org/>
- Firmware + simulator: <https://github.com/emfcamp/badge-2024-software>
- Official 2026 input example: <https://github.com/emfcamp/badge-2026-apps-spaceagon-test>
- Community: Matrix `#badge:emfcamp.org` · IRC `#emfcamp-badge` (libera) · badge@emfcamp.org
