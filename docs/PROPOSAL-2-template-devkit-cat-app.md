# Proposal 2: Template repo + dev kit + "Cat & Yarn" ambient example app

> Status: **awaiting sign-off — no code written yet.** Supersedes/extends `PROPOSAL.md`.
> Grounded in a second research pass (2026-07-18): graphics/sprite pipeline, IMU physics &
> ambient-app viability, and CI/template/theming/flags precedent — all verified against
> firmware source, the app-store backend, and ~10 community app repos (see
> `docs/research/09-cat-app-feasibility.md`).

## Verdict up front

Everything in the brief is buildable on this badge, and the research killed zero features:

- **Ambient app is viable**: Tildagon OS has *no* screen timeout, no dimming (the backlight
  isn't even software-controllable), and nothing ever kills a long-running foreground app.
  It runs until the battery hits the 3.5 V cutoff. `autoexec.bat` can boot the badge
  straight into the app.
- **Accelerometer physics is proven**: 4 independent sources agree on the axis mapping
  (`acc[1]` → screen x, `acc[0]` → screen y, no sign flips), reads are free (100 Hz cached
  by a FreeRTOS task), and community apps already do tilt physics with deadzones.
- **Sprites work**: PNG with transparency, decoded once into a persistent texture cache
  (32 slots), rotate/flip/scale via ctx transforms, `image_smoothing = 0` for pixel art.
- **The battery floor ring is a two-liner**: `ctx.arc(0, 0, ~114, ...)` with `line_width`
  — radius 115-ish is the proven "edge of the round screen" geometry.
- **Nobody has built this**: the ecosystem has a pettable cat face, screensavers, and an
  IMU gauge cockpit — but nothing combining tilt physics + creature + ambient battery
  display. The niche is open.

---

## Part A — The example app: **Cat & Yarn** (ambient toy)

### Concept

A ball of yarn rolls around the round screen under real gravity (tilt). One or more cats
chase it. If the ball reverses direction and would roll past a cat, the cat startles and
jumps. The screen's outer edge is "the floor": a thin ring color-coded by battery level.
Left running as an ambient desk/lanyard toy.

### Geometry (240×240 round display, origin center, r=120)

| Element | Spec | Pixels |
|---|---|---|
| Yarn ball | 10% of screen height (diameter) | **24 px** (r=12) |
| Cat sprite | 8% of screen height incl. tail | **19 px** tall (on a 24×24 transparent PNG canvas) |
| Floor ring | thin border at screen edge | radius ~114, `line_width` ~5 (play area = circle r ≈ 109) |

### Rendering plan (per research)

- **Yarn ball: vector.** A filled circle + 3–4 arc "strands"; drawn inside
  `save() / translate(bx,by) / rotate(θ) / … / restore()` so the strand pattern visibly
  rolls. θ integrates ball speed ÷ radius. Vector is the platform's native idiom (the whole
  OS UI is vector) and dodges sprite-rotation entirely.
- **Cats: tiny PNG sprite frames.** ~24×24 transparent PNGs (badgemon ships ~700-byte
  32×32 PNGs), `ctx.image_smoothing = 0`, horizontal flip via negative `ctx.scale`
  (badgemon's exact trick). Frame set per cat skin: idle×2, run×2–3, fright-jump×2,
  sleep×1 → ≤8 frames/skin, comfortably under the 32-slot texture cache.
  Assets at `/apps/<dir>/assets/`, absolute paths (required), pre-warmed once at startup
  to avoid a first-draw hitch.
- **Floor ring:** full-circle stroke, **color-only** battery indication (decided —
  no arc-length mode).
- **Frame budget:** update/draw cap is 20 fps; tildenstein pushes 60+ vector rects + bezier
  spiders per frame, so ring + ball + 1–3 cat images is easy. When the ball settles and
  cats sleep, `update()` returns `False` → no redraws (scheduler skips rendering).

### Physics (all constants verified from firmware/community source)

```
ax_screen = k · acc[1]          # imu.acc_read(), m/s², ±2 g, free to call per frame
ay_screen = k · acc[0]          # no sign flips — confirmed by 4 sources incl. the official sim
deadzone ≈ 0.8 m/s²             # tildenstein's IMU_DEAD_ACC
optional lanyard rest-offset on acc[0] (tildenstein uses −5.5) — a "hanging mode" flag
v += a·dt; v *= friction; p += v·dt        (dt = delta_ms / 1000, ~50 ms ticks)
circular boundary: if |p| > R_play − r_ball → reflect along normal p/|p|, damped bounce
```

No existing app constrains physics to the round screen — ours would be the first (trivial
math, nice novelty).

### Cat behavior (state machine per cat)

`IDLE → CHASE → FRIGHT → CHASE …` (+ `SLEEP` after long ball-stillness)

- **CHASE**: steer toward the ball with capped speed + turn rate; run animation, flip
  sprite by direction of travel.
- **FRIGHT** (the brief's jump): trigger when the ball's velocity flips sign along the
  ball→cat axis (dot-product sign change) while within a proximity radius — i.e. "it was
  coming, changed its mind, and would roll past me". Cat plays the startle frames with a
  small vertical hop offset (and an optional "!" puff), brief cooldown, then resumes chase.
- **SLEEP**: ball still for N seconds → curl up; any ball movement or a prox-sensor wave
  wakes them.

### Battery floor color

- Poll `power.BatteryLevel()` at **1 Hz max** (each call is a fresh PMIC I2C read — never
  per-frame), smooth with an EMA (the level is a noisy linear voltage map), lerp color
  green → amber → red through the theme palette.
- Subscribe to `RequestChargeEvent` / host-attach events: while `"Fast Charging"`, pulse or
  sweep the ring instead (level jumps discontinuously when charging starts — the state
  events let us switch display mode instead of showing the jump).

### Spaceagon-specific garnish (flagged, optional)

- **Touch ring petting**: the 12 touch pads sit exactly on the rim = the floor ring. Stroke
  the rim near a cat → purr animation. (2026-only; gated on `detect_frontboard()`.)
- **Proximity sensors**: hand-wave wakes sleeping cats.
- **Joystick**: nudge the ball manually (fire = drop a treat?). Later.

### Manifest & category

Category **`Apps`** (valid enum: Badge/Music/Media/Apps/Games/Background/Pattern — there is
no "Toys"). A stripped `Background`-category build (ball drifting behind the launcher menu)
is a possible later Easter egg, but Background apps get no input and only run under the
menu — the real app must be a normal foreground app.

### What needs real hardware (can't be simulated — sim has no IMU-z, no touch, no compass,
and always boots as a 2024 board)

measured FPS with the full scene · battery-drain soak test (no published runtime figures
exist; OS cuts off at Vbat < 3.5 V) · axis-sign sanity check on production 2026 hardware ·
touch-pad chatter characteristics · multi-hour GC/heap stability.

---

## Part B — Template repo + dev kit + pipelines

### Repo becomes a GitHub **template repository** — nothing more

Per clarification: "template" means the GitHub feature only — the repo is marked as a
template so "Use this template" spins up a new repo from it (copies files as a single
squashed commit; does NOT copy settings/secrets/topics/history — the README documents the
one-time setup steps a fresh copy needs: the `tildagon-app` topic for same-repo store
publishing, plus a `PUBLISH_TOKEN` PAT only if mirror-repo publishing is used).
No in-codebase scaffolding machinery. Adding an app *inside* the monorepo is just copying
`apps/_example/` (the Cat & Yarn app doubles as the reference layout).

### Layout (delta from Proposal 1)

```
spaceagon-mono/
├── apps/
│   └── cat-yarn/                  # the example app (store-shaped: app.py + tildagon.toml + assets/)
├── libs/
│   ├── input/                     # action-map input layer (Proposal 1)
│   ├── engine/                    # NEW: tick loop helpers, vec2 math, circular-bounds physics,
│   │                              #      sprite/animation helper, state-machine base
│   ├── theme/                     # NEW: theming engine (below)
│   ├── flags/                     # NEW: feature flags (below)
│   ├── ui/  sensors/  util/
├── tools/                         # vendor.py, deploy.py, release.py, sim.py (wraps firmware sim)
├── .github/workflows/             # ci.yml
├── Justfile                       # dev entry points (just sim cat-yarn, just deploy cat-yarn, …)
└── pyproject.toml                 # uv-managed; ruff, pytest, pyright + micropython-esp32-stubs
```

### Theming engine (confirmed)

- Firmware precedent: zero theming beyond `app_components/tokens.py`, whose `ui_colors`
  dict maps semantic names → rgb tuples **or callables** (gradients), consumed by
  `set_color(ctx, name)`. We mirror that shape exactly for drop-in interop.
- **No dataclasses on-badge** (module doesn't exist in MicroPython) → themes are plain
  dicts: `THEMES = {"spaceagon": {"background": (...), "floor_ok": (...), "floor_low":
  (...), "cat_primary": (...)}, "mono": {...}, ...}`.
- Selected via one settings key (`spaceagon_theme`), default defers to the firmware's
  frontboard palette so apps match OS chrome out of the box. Cat app: themes swap
  background/floor/cat colors (e.g. "space", "cream", "void cat").

### Feature flags

Two tiers, matching how the platform actually works:

1. **Runtime flags** — thin wrapper over the badge `settings` module (flat shared
   `/settings.json`; `set(k, None)` deletes; nothing auto-saves). Namespaced
   `spmono_<app>_<flag>`, e.g. `spmono_catyarn_max_cats`, `..._ring_mode`
   (color-only | color+arc), `..._petting`, `..._hanging_mode`, `..._debug_overlay`
   (fps + `gc.mem_free()`, the badgemon profiling pattern).
2. **Build-time constants** — `tools/vendor.py` generates a `_build.py` per app at
   release (`DEBUG=False`, `VERSION="…"`, flavor), so dev-only code can be gated hard and
   stripped from store builds. (Precedent: BadgeBot's release pipeline builds artifacts
   into a release branch.)

### CI (GitHub Actions — "nice but beta-appropriate")

| Job | What | Precedent |
|---|---|---|
| lint | ruff check + format check (uv) | firmware pre-commit |
| unit | pytest on CPython with **MicroPython stub conftest** (stub `machine`/`imu`/`settings`/`time.ticks_*`; hand-written `events.input` mini-impl) — tests physics, cat state machine, flags, theme | area/racecondition's proven approach |
| sim-smoke | checkout firmware at pinned SHA, Python 3.10, symlink `apps/<x>` into `sim/apps/`, `SDL_VIDEODRIVER=dummy python run.py --screenshot <x>.App`, upload screenshot artifact | firmware sim.yml + BadgeBot |
| manifest | lightweight `tildagon.toml` sanity check in Python (required fields, category enum, author ≤32 / description ≤140) — full store-schema validation only matters for store publishing, which is out of scope | docs publish.md limits |

### Distribution (decided: NO mirror repos — this mono is the template codebase)

- Primary path: **sideload** — `just deploy <app>` runs `vendor.py` (flatten app + its
  declared `libs/` + stamp `_build.py`) then `mpremote cp` to `/apps/<app>/` on the badge.
- Apps stay **store-shaped** anyway (root-level `app.py` + `tildagon.toml` inside their
  folder) — that costs nothing and keeps the door open: if an app ever warrants store
  publishing, `vendor.py`'s output can be pushed to a standalone repo by hand (topic
  `tildagon-app` + a release). No automation for that is in scope.
- If we ever do publish manually: use fixed-width zero-padded versions (`1.00.00`) —
  the badge's update check is a lexicographic string compare and breaks on `0.9 → 0.10`.

---

## Decision log

| Decision | Outcome |
|---|---|
| Template | GitHub template repository only — no in-repo scaffolding (owner, 2026-07-18) |
| Theming engine | Confirmed (owner) |
| Battery ring | **Color-only** (owner) |
| Mirror-repo publishing | **Dropped** (owner, 2026-07-18) — then **amended** (owner, 2026-07-18): a `publish.yml` workflow flattens an app to its standalone store repo on manual dispatch (first publish) and auto-releases on `main` when the manifest version is bumped. Sideload remains the dev path. — **Amended again** (owner, 2026-07-18): this repo (`bat-cat`) is itself the store repo; `publish.yml` force-pushes the flattened app to a same-repo `store` branch and targets releases at it (built-in `GITHUB_TOKEN`, no PAT, first publish automatic). Mirror mode kept only for a future second app. |
| App name / category | Store name **bat-cat**, category **Badge** (owner, 2026-07-18); dev folder stays `apps/cat_yarn/`. |
| Cat art | Pixel-art PNG frames (default recommendation, not objected) |
| v1 scope | Tilt ball + 1–2 cats + fright-jump + battery ring; petting/prox/multi-cat behind flags (default recommendation, not objected) |
