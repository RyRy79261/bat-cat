# Research: Cat & Yarn app + template/dev-kit feasibility

> Snapshot 2026-07-18. Three research passes (graphics/sprites, IMU physics + ambient
> viability, CI/template/theming/flags), all verified against firmware source
> (`badge-2024-software` @ v2.1.1), the app-store backend, and ~10 community app repos.

## Graphics & sprites

- **Image formats**: JPEG, PNG, GIF (first frame only) via stb_image; SVG rejected.
  PNG alpha supported (premultiplied) → transparent sprites work.
  (`components/ctx/ctx_config.h:87-90`, `ctx.h:55247,55300-55312`)
- **Paths must be absolute VFS paths** (`/apps/<dir>/assets/foo.png`); resolve your install
  dir by scanning `os.listdir("/apps")` (badgemon's `config.py` pattern — store install
  dirs are `<owner>_<repo>` flattened).
- **Texture caching**: decoded once, cached by path in a **32-slot** cache; textures drawn
  every frame are never evicted; decode does NOT happen per frame. Keep distinct sprite
  paths well under 32. First draw pays the decode cost → pre-warm at startup.
  (`ctx.h:55244+`, `ctx_config.h:60`, confirmed by custard-cream-badge code comment)
- **Size guidance**: docs say keep files ≈≤30 KB (crash risk = heap exhaustion; 40 KB
  full-screen JPEG demonstrably works). Small sprites are trivial: a 24×24 decode is
  ~2.3 KB RGBA.
- **Transforms**: `ctx.image` fully respects the CTM — rotate (sponsor-logos rotates JPEGs
  by IMU angle), flip via negative `ctx.scale` (badgemon), scale. `image_smoothing = 0`
  for pixel art.
- **Vector at 20 fps is proven**: tildenstein redraws ~60 rect columns + multi-bezier
  spider sprites per frame, all vector; the entire OS UI is vector (zero `ctx.image` calls
  in firmware). Caveat: `CTX_MAX_EDGES 255` per filled path — keep shapes simple.
- **Frame cadence**: 20 fps ceiling (0.05 s loop); `update()` returning `False` skips the
  redraw entirely — the ambient idle-mode lever. `display.get_fps()` + `gc.mem_free()`
  (badgemon) for on-badge profiling. No published FPS numbers exist → measure on hardware.
- **Ring drawing**: `arc(x, y, r, from, to, direction)` — radians from +x axis, direction
  boolean (True = counter-clockwise); `line_width` attribute + `.stroke()`. Proven edge
  ring: radius 115–116, width 4–5 (badgemon battle ring, BadgeBot sensor ring). Partial
  ring from 12 o'clock: `arc(0,0,114, -π/2, -π/2 + f·2π, 0)`.

## IMU & physics

- **Axis mapping (4 concordant sources**: snake-imu comments, firmware
  `simple_tildagon.py`, the official simulator's WASD `GravityInput`, tildenstein):
  `acc[0]` +ve = bottom edge down = screen **+y**; `acc[1]` +ve = right edge down = screen
  **+x**. With ctx's y-down center origin: **no sign flips**. No mount matrix in firmware —
  raw BMI270 axes.
- Accel config: ±2 g, 100 Hz ODR, AVG4 filter. A FreeRTOS task polls at 100 Hz and caches;
  `imu.acc_read()` just copies cached floats — **free to call every frame**.
- Community physics practice: deadzone ≈0.8 m/s²; lanyard rest-angle offset (tildenstein
  subtracts −5.5 on acc[0] for hanging badges); `dt = delta_ms/1000`; delta is integer ms.
- **Nobody constrains motion to the round screen** (snake uses a square, others
  rectangles) — circular boundary reflection is novel-but-trivial.

## Ambient-app viability

- **No screen dimming/sleep/timeout exists anywhere in the OS**, and the GC9A01 backlight
  is not wired to a controllable pin (`backlight_used = 0`) — screen is 100% on while
  powered, by design.
- **Nothing auto-kills/minimises apps** — only an uncaught exception stops one. Foreground
  apps run indefinitely; when unfocused, `update()` blocks until refocus but
  `background_update()` keeps running.
- **Power-off**: OS shuts down at Vbat < 3.5 V (no USB), polled every 10 s. Battery
  2000 mAh; **no published runtime figures** — needs a soak test. Save power by emitting
  `PatternDisable` (LEDs off) and idle-skipping redraws.
- **Category "Background" is a launcher wallpaper**, not an ambient-app vehicle: installed
  to `/backgrounds`, drawn under the menu text, receives no input. The toy must be a
  normal foreground app. Valid store categories: Badge, Music, Media, Apps, Games,
  Background, Pattern (no "Toys").
- **`/autoexec.bat`**: line 1 substring-matched against launcher menu names; auto-launches
  at boot — users can boot straight into the toy.
- **Battery API**: `power.BatteryLevel()` → float 0–100, **fresh PMIC I2C read per call**
  (poll ≤1 Hz), discharging = noisy linear map of Vbat 3.5→4.14 V (smooth with EMA);
  different formula while charging → level jumps at plug/unplug. Charge-state changes and
  USB attach/detach arrive as eventbus events (`RequestChargeEvent`,
  `RequestHostAttach/DetachEvent`); `BatteryChargeState()` ∈ {Not Charging, Pre-Charging,
  Fast Charging, Terminated}.
- **Interaction**: focused foreground app receives everything, including the 12-pad touch
  ring (`TOUCH01–12`, physically on the rim = on our "floor") and both prox sensors —
  ideal petting inputs. Clear button states before `minimise()`.

## Prior art (niche check)

ashhhleyyy/tildagon-cat (pettable cat face, no motion) · robmckinnon/tildagon-and0r
(IMU + battery annular gauges — closest to our ring) · emericklaw/tildagon-app-battery-meter ·
saukothari/tildagon-spymato · screensaver apps (mystify, wormhole, EMF-Spinner) ·
badgemon (creature RPG). **Nothing combines tilt physics + creature + ambient battery
display.**

## Template / CI / theming / flags

- **CI precedent**: firmware `sim.yml` (Python 3.10, `pip install -r sim/requirements.txt`,
  `SDL_VIDEODRIVER=dummy python run.py --screenshot`) and `tests.yml` (unittest).
  Community: BadgeBot runs pytest inside the sim tree (fork-with-submodule; ⚠ never import
  `sim/run.py` at pytest collection time — it replaces `sys.meta_path`);
  **area/racecondition tests badge code with hand-rolled MicroPython stubs** (no sim) —
  fast and robust; they hand-wrote an `events.input` mini-impl after a MagicMock stub let a
  firmware change slip through. Both approaches are complementary.
- **Sim from an external repo**: `sim/apps/<dir>/` + `__init__.py` exporting the class;
  `run.py [--screenshot] <dir>.<Class>` replaces the Launcher and boots your app; symlink
  from our repo works in CI (checkout firmware at pinned SHA; use Python 3.10, not runner
  default).
- **Mirror-repo automation**: `danharrin/monorepo-split-github-action` v2.4.5 (active,
  May 2026) or scripted subtree-split/push; auth via fine-grained PAT (deploy keys =
  least-privilege but one secret per mirror). Must-dos verified against store source:
  release must be **created in the mirror** (tag alone is invisible;
  `gh release create --repo`), topic `tildagon-app` must be **on the mirror** (set
  idempotently via `gh api PUT /repos/{o}/{r}/topics`), store takes newest release by
  *creation time*.
- **Manifest validation in CI**: the store's zod schema (`packages/tildagon-app`) is
  `private: true` on npm but runnable by checking out `badge-2024-app-store` + `npm ci` +
  a tiny script. Docs limits: author ≤32 chars, description ≤140.
- **Version scheme**: badge update check is `v1.split(".") > v2.split(".")` (string
  lists!) — `0.9→0.10` and `9.x→10.x` break. Use fixed-width zero-padded (`1.00.00`).
- **Template mechanics**: GitHub template repos copy files (single squashed commit), NOT
  settings/secrets/topics/history. For in-repo app generation, **Copier** is the
  2026-preferred tool (typed prompts, `copier update`); cruft only for cookiecutter estates.
- **Theming**: no theme/palette concept exists in firmware beyond
  `app_components/tokens.py` — `ui_colors` semantic dict (values: rgb tuple **or
  callable/gradient**) resolved by `set_color`. Mirror that shape. **No `dataclasses` on
  badge** → plain dicts/classes.
- **Feature flags**: badge `settings` module = lazy flat `/settings.json` shared with
  firmware keys (`wifi_*`, `pattern_*` …) — prefix-namespace ours; `set(k, None)` deletes;
  explicit `save()`; last-writer-wins with the Settings app, keep windows short. BadgeBot's
  "flavours" are hardware variants, not CI flavours — its actual precedent is
  `dev/build_release.py` (allowlist → mpy-cross → release branch), supporting our
  vendor-time `_build.py` constants idea.

## Open questions (hardware or badge-team)

- Measured FPS for the full scene; battery-drain per hour (screen on, LEDs off/on).
- acc[2] sign when lying flat (only matters for lie-flat detection).
- Touch-pad chatter/repeat behavior for stroke detection.
- Multi-hour GC/heap stability of a continuously-drawing MicroPython app.
- First-draw decode hitch and pre-warm effectiveness.

## Key sources

Firmware: `components/ctx/ctx_config.h`, `ctx.h`, `drivers/gc9a01/{display.c,mp_uctx.c}`,
`modules/{app.py,tildagonos.py,settings.py}`, `modules/system/{scheduler,launcher,power,
patterndisplay}/`, `modules/lib/simple_tildagon.py`, `drivers/tildagon_power/mp_power.c`,
`components/flow3r_bsp/{flow3r_bsp_imu.c,flow3r_bsp_display.c}`, `sim/{run.py,fakes/}`.
Community: badgemon, tildenstein, custard-cream-badge, tildagon-sponsor-logos, BadgeBot,
racecondition, emf-duckfacts-tildagon, tildagon-cat, tildagon-and0r, battery-meter,
snake-imu. Store: `badge-2024-app-store/packages/…/sources/github.ts`,
`packages/tildagon-app/`. Docs repo: `docs/tildagon-apps/reference/ctx.md`,
`development.md`, `publish.md`.
