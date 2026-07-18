# The Tildagon OS app programming model

> Research snapshot: 2026-07-18, verified against firmware source (`emfcamp/badge-2024-software`
> @ `beef903`, 2026-07-16) and docs source (`emfcamp/badge-2024-documentation` @ `8c0254a`).

Tildagon OS is a MicroPython fork (ESP-IDF based, ctx graphics borrowed from the flow3r
badge). Apps are plain Python: subclass `App`, export the class, done. No build step.

## The App base class (`modules/app.py`, import as `from app import App`)

```python
from app import App

class MyApp(App):
    def __init__(self):
        super().__init__()
        # set up state, input helper, event subscriptions

    def update(self, delta):        # ~every 0.05 s while foregrounded; delta is MILLISECONDS
        return False                # False (the default) = "nothing changed", skips redraw
                                    # returning None/anything-else triggers draw()

    def draw(self, ctx):            # paint the screen; called after each non-False update
        ...

    def background_update(self, delta):   # ~every 0.05 s ALWAYS, even when minimised
        ...

__app_export__ = MyApp              # required: how the launcher finds your class
```

Key lifecycle facts (all from firmware source):

- **`update(delta)`** — `delta` is milliseconds (`time.ticks_diff` of `ticks_ms`), despite
  the type hint saying float. Docs examples divide by 1000.
- **`draw(ctx)`** — only the app on top of the foreground stack gets drawn (plus "on top"
  overlay apps like the notification service). If you use `self.overlays`, call
  `self.draw_overlays(ctx)` yourself.
- **`background_update(delta)`** — runs regardless of focus. Button states do **not** update
  while backgrounded. (Doc bug: their example omits the `delta` param — the firmware passes it.)
- **`minimise()`** — pops the app off the foreground stack; it keeps running in background.
  Convention: CANCEL button → `self.button_states.clear(); self.minimise()`. *Always provide
  a way out of your app.*
- **`terminate(restore_pattern=False)`** — full stop (needs Tildagon OS ≥ v2.0.0). Stopping
  auto-deregisters all your eventbus handlers; minimising does not.
- **Async apps**: override `async def run(self, render_update)` for full control — await
  dialogs, `await render_update()` to trigger a draw. The scheduler wraps it in an asyncio task.
- **Crashes are contained**: an exception in `update`/`draw`/a handler stops *your* app,
  prints the traceback to serial, and shows a "<ClassName> has crashed" notification. The OS
  survives.

## Drawing: the `ctx` vector API

Passed into `draw(ctx)`; never construct it. Canvas-like, chainable (most methods return self):

- **Coordinates**: origin (0,0) at the **center** of the round 240×240 display; x right,
  y down; visible span −120..120. Full-screen fill: `ctx.rgb(0,0,0).rectangle(-120,-120,240,240).fill()`.
- **Color**: `rgb(r,g,b)` / `rgba(...)` take **floats 0.0–1.0**; `gray(v)`; linear/radial
  gradients with `add_stop`.
- **Shapes/paths**: `rectangle`, `round_rectangle`, `arc(x,y,r,from,to,dir)`, `begin_path`,
  `move_to`, `line_to`, `curve_to`, `quad_to`, `close_path`, then `stroke()` / `fill()` / `clip()`.
- **Text**: `ctx.font_size = 24; ctx.text_align = ctx.CENTER; ctx.text("hi")`; `text_width()`;
  font 0 is the EMF Camp font (custom glyphs incl. hexagons, arrows, duck, shark…).
- **Images**: `ctx.image(path, x, y, w, h)` — keep them small (~30 KB guidance); big images
  crash apps (RAM).
- **Transforms/state**: `translate/scale/rotate` (radians), `save()`/`restore()`.

## UI components (`app_components`)

`from app_components import Menu, Notification, YesNoDialog, TextDialog, clear_background`

- **Menu**(app, items, select_handler, back_handler, …) — call its `update(delta)` + `draw(ctx)`
  from yours. **Must call `menu._cleanup()` before replacing a menu** (else stale handlers fire).
- **Notification**(message) — toast, auto-closes ~5 s. System-wide: emit `ShowNotificationEvent`.
- **YesNoDialog / TextDialog** — sync (handlers + `_cleanup()`) or async
  (`self.overlays = [dialog]; result = await dialog.run(render_update)`) styles.
- **`app_components.layout`** — `LinearLayout`, `TextDisplay`, `DefinitionDisplay`,
  `ButtonDisplay` (what the firmware Settings app uses); forward events via
  `await self.layout.button_event(event)`.
- **`app_components.tokens`** — `display_x/display_y = 240`, font-size constants,
  `clear_background(ctx)`, `set_color(ctx, color)`, frontboard-aware `colors`/`ui_colors`,
  `symbols` glyph dict.
- **`app_components.background.Background`** — draw the user's chosen background behind your app.

## The eventbus (`from system.eventbus import eventbus`)

- `eventbus.on(EventType, handler, app)` / `on_async(...)` / `emit(event)` /
  `await emit_async(event)` / `remove(type, handler, app)` / `deregister(app)`.
- Events subclass `events.Event`; `event_type` can also be a **string** matched against an
  event's `.type` (dict events supported) — handy for custom cross-app events.
- All input events have `requires_focus = True` → delivered **only to the focused app**
  (top of the foreground stack).
- Remove handlers on minimise, or you'll keep processing while backgrounded (input events
  won't arrive, but other events will).

## App anatomy on disk — three contexts

1. **Published (app store)**: one GitHub/Codeberg repo per app, `app.py` (with
   `__app_export__`) + `tildagon.toml` at the **repo root** — see `06-publishing.md`.
2. **Installed on badge**: extracted to `/apps/<owner>_<repo>/`; the installer deletes
   `tildagon.toml` (badge has **no TOML parser**), writes `tildagon.json` + a
   `metadata.json`; the launcher imports `apps.<folder>.app` and instantiates
   `__app_export__`. Backgrounds → `/backgrounds`, Patterns → `/pattern`.
3. **Dev sideload**: copy the folder to `/apps/<folder>/` with a dev-only `metadata.json`
   `{"name": "...", "path": "apps.<folder>.<module>"}` — remove before publishing. See
   `05-toolchain.md`.

### Special app types

- **Background** apps: export `__Background__ = Class`; only `update`/`draw` called; category
  `Background`.
- **Pattern** apps (drive the 12 ring LEDs): implement `self.fps` + `next(self)` returning 12
  RGB(0–255) tuples; must export **both** `__pattern_export__` and `__Pattern_Export__`
  (firmware/app-store casing mismatch).
- `autoexec.bat` at badge root (containing an app's menu name) auto-launches it at boot.

### Persistence

`import settings` → `settings.get(key, default)`, `set`, `save`, `load`. It's the shared
`/settings.json` (WiFi creds etc. live there too) — namespace your data under one unique key.

### Capabilities (new for 2026)

Apps can declare in their manifest `[[metadata.capabilities]]` entries with
`required = true|false` and features like `{ type = "2026 Frontboard" }`,
`{ type = "TildagonOSMinimumVersion", version = "..." }`, a hexpansion `{vid, pid}`, or a
capability URL; plus `providedCapabilities`. Runtime checks:
`system.capabilities.utils.get_unmet_requirements(...)`, `get_frontboard()`,
`get_running_apps_by_capability(url)`. The app-store API can filter on these.

## MicroPython platform notes

- MicroPython pinned at **v1.28.0** (submodule commit `e0e9fbb`), ESP-IDF v5.5.1, target ESP32-S3.
- Latest Tildagon OS release: **v2.1.1** (2026-07-16).
- Frozen-in libraries usable by apps: `asyncio` (uasyncio API), `requests`, `umqtt.simple`/
  `umqtt.robust`, `ntptime`, `mip`, `aioble` (BLE), `aioespnow` (ESP-NOW), plus badge modules
  (`wifi`, `settings`, `tildagonos`, `display`, `imu`, `power`, `pd`).
- No pip on the badge; **vendor everything** your app needs inside its folder. `app.mpy`
  (mpy-cross compiled) is accepted in place of `app.py` but plain `.py` is the norm.
- Memory is tight (2 MB PSRAM): `gc.collect()` aggressively, keep assets small.
- The simulator runs CPython — CPython-only syntax may pass in sim and fail on badge; keep
  code MicroPython-compatible.

## Key sources

- <https://tildagon.badge.emfcamp.org/tildagon-apps/development/>
- <https://github.com/emfcamp/badge-2024-software> — `modules/app.py`,
  `modules/system/scheduler/__init__.py`, `modules/system/eventbus.py`,
  `modules/app_components/`, `modules/system/launcher/`
- <https://tildagon.badge.emfcamp.org/tildagon-apps/reference/ctx/>,
  `.../reference/ui-elements/`, `.../reference/eventbus/`
- <https://tildagon.badge.emfcamp.org/tildagon-apps/patterns/>, `.../backgrounds/`,
  `.../configuration/`, `.../autoexec/`
- Capabilities: `docs/capabilities/index.md` in the docs repo
