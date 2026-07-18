# Toolchain: how we code, run, upload, debug

> Research snapshot: 2026-07-18. Commands verified against the docs source and firmware repo
> at this week's commits.

## TL;DR loop

1. Write plain MicroPython — **no build step**, apps ship as `.py` source.
2. Iterate in the **desktop simulator** (fast, no hardware).
3. Sideload to a real badge with **mpremote** for hardware features (and for ALL 2026 inputs —
   the simulator doesn't do joystick/touch/prox yet).
4. Publish via GitHub release (see `06-publishing.md`).

## The simulator (`sim/` inside the firmware repo — no separate repo)

CPython + pygame; the real `ctx` C renderer compiled to WASM (wasmtime); firmware modules
replaced by fakes.

```sh
git clone https://github.com/emfcamp/badge-2024-software
cd badge-2024-software/sim
# needs Python 3.10 (Pipfile pin); macOS: brew install sdl2 sdl2_image sdl2_mixer sdl2_ttf pkg-config
pip install --user pipenv
pipenv install
pipenv run python run.py
```

- Apps go in `sim/apps/<YourApp>/` with `app.py` (+`__app_export__`), `__init__.py`
  (`from .app import YourApp`), and `metadata.json` (`callable`, `name`, `category`, `hidden`).
- Undocumented but useful: `pipenv run python run.py <module>.<Class>` boots straight into
  your app; `--screenshot` renders one frame headlessly (CI uses `SDL_VIDEODRIVER=dummy`);
  deps also installable via `pip install -r sim/requirements.txt`.
- **What works**: display (pixel-accurate ctx), the 6 buttons (mouse or keys `a`–`f`,
  remappable via `config.py`), LED ring, accelerometer tilt via WASD, real HTTP (the
  `urequests` fake wraps host `requests`).
- **What does NOT work**: all 2026 inputs. `sim/fakes/frontboard2026.py` is a no-op stub,
  and worse: the sim's fake `machine.I2C.scan()` returns `[]`, so `detect_frontboard()`
  **always defaults to the 2024 board** — the entire `TwentyTwentySix` path (joystick,
  touch, prox) never even loads, and there is no config switch to force 2026. Also no
  compass, no BLE/ESP-NOW, gyro returns constants. README's own words: "No support for
  most things."
- Sim is CPython, badge is MicroPython — CPython-only syntax can pass in sim and die on badge.

Web emulator (<https://emulator.badge.emfcamp.org/>): browse the OS and published store apps,
but **cannot run your own apps** (as of 2026-06-21).

## Sideloading to a real badge (mpremote)

Plug USB-C into the **USB IN** port. Then:

```sh
pip install mpremote          # standard MicroPython tool
mpremote mkdir apps
mpremote mkdir apps/myapp
mpremote cp path/to/app/dir/* :/apps/myapp/
# hold the "reboop" button ~2s to restart the badge
```

Dev-only `metadata.json` required in the app dir (remove before publishing):

```json
{ "name": "My App", "path": "apps.myapp.app" }
```

Apps live at `/apps/<folder>/` on the badge (`/backgrounds`, `/pattern` for those types).

## Debugging

- `mpremote` gives a serial REPL: **Ctrl-C** stop, **Ctrl-D** soft-reset (stay attached),
  **Ctrl-X** exit. Launch your app from the badge menu and watch `print()` output and
  tracebacks live.
- Crashing apps are stopped by the scheduler with an on-badge "<ClassName> has crashed"
  notification and a traceback on serial; the OS survives. There's no logging framework —
  `print()` is it.

## Firmware (you rarely touch this)

- **Flash**: web flasher at <https://emfcamp.github.io/badge-2024-software/> (Chromium-only;
  hold **boop** while plugging USB for bootloader mode; "Install Tildagon" erases data).
- **OTA**: on-badge `Update` menu app (WiFi) — pulls `micropython.bin` from the firmware
  repo's GitHub releases.
- **⚠ Update firmware BEFORE fitting a Spaceagon frontboard** or only the joystick will work.
- Building from source needs Docker + `ghcr.io/emfcamp/esp_idf:v5.5.1` — app devs never
  need this.

## Dependencies

No pip/mip flow for apps — **vendor everything** in the app folder; the store tarball ships
and extracts the whole tree, so multi-file apps and vendored libs work fine. `app.mpy`
(mpy-cross) is accepted but plain `.py` is the ecosystem norm.

## Editor / typing / testing

- Docs recommend no specific editor and reference no stubs; firmware vendors no-op
  `typing`/`typing_extensions` shims so `typing` imports don't crash on-badge.
- Off-badge unit testing works under CPython using the sim's fakes as importable modules —
  the firmware repo itself runs `python -m unittest discover -t . -s tests -v` plus a
  headless-sim boot check in CI. Community example: space-scanner tests logic modules
  off-badge and uses a UDP-loopback desktop harness.
- Practical monorepo takeaway: keep pure-logic modules import-clean (no firmware imports) so
  they're trivially testable on CPython; isolate firmware-touching code behind small adapters.

## Key sources

- <https://tildagon.badge.emfcamp.org/tildagon-apps/simulate/> (docs source `simulate.md`)
- <https://tildagon.badge.emfcamp.org/tildagon-apps/run-on-badge/> (`run-on-badge.md`)
- <https://tildagon.badge.emfcamp.org/using-the-badge/flash-the-badge/>
- `sim/README.md`, `sim/Pipfile`, `sim/run.py`, `sim/fakes/`, `.github/workflows/` in
  <https://github.com/emfcamp/badge-2024-software>
- <https://docs.micropython.org/en/latest/reference/mpremote.html>
