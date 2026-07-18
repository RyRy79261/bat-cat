# Proposal: spaceagon-mono architecture & stack

> Status: **awaiting sign-off — no code written yet.** Everything below is grounded in the
> research under `docs/research/` (source-verified against the firmware, docs, and app-store
> repos as of 2026-07-18).

## What we're building on (30-second recap)

- The Spaceagon = EMF 2026 front board on the 2024 Tildagon platform. Apps are **plain
  MicroPython** (v1.28.0) on **Tildagon OS v2.1.1**: subclass `App`, implement
  `update(delta)`/`draw(ctx)`, export `__app_export__`. No build step, no review process.
- All input (buttons, joystick, touch ring, proximity) arrives as
  `ButtonDownEvent`/`ButtonUpEvent` with a hierarchical `Button` object; sensors via `imu`,
  `power`, `tildagonos` (LEDs), `wifi`, BLE/ESP-NOW.
- **The app store hard-requires one repo per app** (root `app.py` + `tildagon.toml`, a
  release, the `tildagon-app` topic). Sideloading via `mpremote` has no layout constraints.
- The desktop simulator covers display/6-buttons/tilt only — **2026 inputs are untestable
  off-hardware** today.

## Proposed repo layout

```
spaceagon-mono/
├── README.md
├── docs/                        # this research + proposal
├── libs/                        # shared libraries ("common tools")
│   ├── input/                   #   input abstraction layer (see below)
│   ├── ui/                      #   helpers over ctx/app_components (screens, widgets)
│   ├── sensors/                 #   compass heading (w/ calibration), tilt, battery helpers
│   └── util/                    #   settings namespacing, logging shim, version guards
├── apps/                        # one folder per app — each shaped like a publishable app
│   └── <appname>/
│       ├── app.py               #   entry point (subclass App, __app_export__)
│       ├── tildagon.toml        #   store manifest (ready for mirroring)
│       ├── metadata.json        #   dev-only sideload manifest (stripped at release)
│       └── lib/                 #   vendored copy of needed libs/ (generated, gitignored)
├── tools/                       # our dev scripts (deploy, vendor, release)
│   ├── deploy.py                #   vendor libs + mpremote cp an app to the badge
│   ├── vendor.py                #   copy the libs an app declares into apps/<x>/lib/
│   └── release.py               #   build a mirror-repo tree for store publishing
└── pyproject.toml               # uv-managed dev env (linting, stubs, tests, sim glue)
```

### Why this shape

- **Apps stay store-shaped** (root-level `app.py` + `tildagon.toml` inside their folder), so
  the release tool's job is mechanical: vendor libs → copy folder to a mirror repo → tag.
- **Shared code lives once** in `libs/`, but is **vendored into each app** at deploy/release
  time because the platform has *no* cross-app dependency mechanism — every store app must
  be self-contained. Vendoring is the ecosystem norm.
- Pure-logic code in `libs/` stays **import-clean** (no firmware imports) where possible, so
  it's unit-testable on CPython without a badge.

## The input abstraction layer (`libs/input`) — the core deliverable

Design (all primitives verified against firmware source):

1. **Actions, not buttons.** Apps declare semantic actions (`"select"`, `"back"`, `"move_n"`,
   `"page_next"`), and an `InputMap` binds them to physical sources:
   - default bindings target `BUTTON_TYPES` (portable across 2024/2026, buttons+joystick),
   - opt-in bindings for `JOYSTICK_BUTTON_TYPES`, `FRONTBOARD_BUTTON_TYPES` (A–F),
     `TOUCH01–12`, `LEFTPROX/RIGHTPROX`,
   - per-app override maps so the same component works in different apps with different keys.
2. **Edge/gesture engine** on top of the raw events (the firmware gives you none of this):
   debounced press (the OS auto-repeats Down events every 200 ms on hold!), release,
   long-press, hold-repeat with acceleration, chords (e.g. C+D), and touch-ring gestures
   (tap zone → clock position, swipe → rotation direction).
3. **Guaranteed exit**: CANCEL → `minimise()` is wired by default in our `BaseApp` so every
   composed app honors the platform convention.
4. **Frontboard-aware**: `detect_frontboard()`-gated feature registration; touch/joystick
   bindings degrade gracefully (or remap) on a 2024 board.
5. Delivered as a mixin/base class (`libs/input` + `BaseApp` in `libs/ui`) so an app is:
   binding table + state + draw code, composable exactly the way you described.

## Recommended stack (recency-audited 2026-07-18, see research 08)

| Purpose | Choice | Why / status |
|---|---|---|
| Language / runtime | MicroPython 1.28.0 (Tildagon OS v2.1.1) | Fixed by platform. Avoid CPython-only syntax (`match` doesn't compile on-badge). |
| Dev env / package mgr | **uv** | 2026 norm. The official sim docs still say pipenv+Py3.10 (works via `sim/requirements.txt` with uv too); our own tooling uses uv regardless. |
| Deploy to badge | **mpremote** (1.28.0) | Still the official/current tool; wrapped by `tools/deploy.py`. |
| Fast iteration | Firmware repo's `sim/` (pinned checkout) | Display/buttons/tilt only. `run.py <module>.<Class>` direct-boot + `--screenshot` for smoke tests. **2026 inputs: real badge only.** |
| IDE support | pyright + `micropython-esp32-stubs==1.28.0.post4` | The current stubs ecosystem (matches MicroPython 1.28 exactly). No Tildagon stubs exist — we can generate thin stubs for `app`, `events.*`, `imu`, etc. as part of `libs/`. |
| Lint/format | **ruff** (0.15.x), `target-version = "py39"`-ish | Ecosystem norm (firmware repo uses it). Explicit target since MicroPython ≈ py3.9/3.10-era syntax. |
| Tests | pytest on CPython for pure-logic modules; sim fakes for integration; real badge for 2026 inputs | Mirrors what the firmware repo and best community apps do. |
| Publishing | Per-app **mirror repos** generated by `tools/release.py` (copy or subtree-split; root layout + `tildagon-app` topic + tagged release) | The only store-compatible path for a monorepo. Version rule: keep components lexicographically ordered (badge's update check breaks on `0.9→0.10`). |
| CI/CD | none for now (per your call) | `tools/release.py` runs manually; trivially GitHub-Actions-able later. |

## Suggested first apps (to prove the composition model)

1. **Input playground** — visualizes every input through our abstraction (doubles as the
   layer's test harness on hardware; the official test app is the reference).
2. **Compass** — `imu.mag_read()` + our calibration + LED-ring "north" indicator (nobody has
   shipped a third-party compass app yet — the field is open).
3. Then whatever you actually want to build, composed from the above.

## Decisions I'd like from you

1. **Repo layout** as proposed (apps store-shaped + vendoring + mirror repos)? The
   alternative — separate repos now — kills the monorepo idea; mirroring is the workaround.
2. **Mirror-repo naming**: e.g. `RyRy79261/spaceagon-<appname>` per app, generated by the
   release script. OK?
3. **2024 backward-compat**: should our input layer degrade gracefully on 2024 Tildagons
   (bigger audience, ~more code) or target Spaceagon-only (simpler)? My lean: build against
   `BUTTON_TYPES` (free portability) and gate touch/joystick extras behind
   `detect_frontboard()` — that's nearly free.
4. Confirm the two starter apps, or name your own.
