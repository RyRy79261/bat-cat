# Verification & recency audit log

How this research was validated (2026-07-18):

1. **7 parallel researchers**, one per dimension (hardware / app model / input / sensors /
   toolchain / publishing / ecosystem), each required to cite primary sources. Because
   `*.emfcamp.org` is blocked from this environment, doc claims were read from the docs
   *source repo* (`emfcamp/badge-2024-documentation`, which builds the site) and API claims
   from actual firmware/app-store source at head commits (all dated 2026-07-14..17, i.e.
   post-EMF-2026 and current).
2. **Adversarial verification pass**: a separate agent attacked the 10 most load-bearing
   claims by re-reading the source files, with line-number evidence. Result: 9 confirmed,
   1 minor correction (manifest `category` may be an array; capabilities are
   `{required, feature}` associations).
3. **Tooling recency audit**: every recommended tool/version was checked live against
   GitHub/PyPI, all rendered **CURRENT** as of 2026-07-18.

## Key confirmations (all source-verified, file+line)

- One-repo-per-app store requirement (root manifest, `releases(first:1)`, identity has no
  path component; installer demands one root dir with `app.py` in it).
- MicroPython pinned at **v1.28.0** (the current latest stable, ~Apr 2026); Tildagon OS
  **v2.1.1** (2026-07-16) is the latest firmware; ESP-IDF v5.5.1.
- Full input model incl. Button parent hierarchy, no-parent TOUCH/PROX, auto-repeat
  (200 ms on 2026; 2024 also repeats ~100 ms after ~500 ms), focus rules.
- Compass QMC6309 @0x7C; `imu.mag_read()` silently returns zeros/stale on 2024 boards.
- IMU contradiction resolved: **BMI270 = production**, LSM6DS3 = prototype fallback
  (firmware probes BMI270 first; docs agree). `imu.id()` is the runtime-safe check.
- Simulator can never exercise 2026 inputs (fake I2C scan ⇒ always detects 2024 board).
- No badge TOML parser; dev `metadata.json` sideload flow; reboop restart.
- On-badge update check is a lexicographic version compare (`0.9 → 0.10` breaks).
- `match` statements: absent from MicroPython v1.28 grammar — sim(CPython)-only trap.

## Recency verdicts (2026-07-18)

| Tool | State | Verdict |
|---|---|---|
| emfcamp/badge-2024-software | v2.1.1 (2026-07-16); still the canonical repo for 2026, no successor repo | CURRENT |
| MicroPython | v1.28.0 is latest stable | CURRENT |
| mpremote | 1.28.0 on PyPI (lockstep with MicroPython); still the documented tool | CURRENT |
| Simulator | pipenv + Python 3.10 pin is what the repo really uses; `sim/requirements.txt` exists (works with uv, unofficially). Py3.10 EOL Oct 2026 | CURRENT (with caveat) |
| Stubs | `micropython-esp32-stubs==1.28.0.post4` (Josverl, 2026-05-20) + pyright is the 2026 setup; **no Tildagon-specific stubs exist** | CURRENT |
| ruff | 0.15.22 (2026-07-16) is the ecosystem norm (firmware repo itself uses ruff, albeit pinned old); set `target-version` explicitly | CURRENT |
| Web emulator | last commit 2026-06-02; still cannot run unpublished apps | CURRENT (limited) |
| App template | hughrawlinson/tildagon-demo still the docs' fork point; no official emfcamp template | CURRENT |
| Web flasher | emfcamp.github.io/badge-2024-software still the flashing path (Chromium-only) | CURRENT |
| PyPI "tildagon" tooling | none exists (7 likely names probed) | n/a |

## Bugs/gotchas discovered along the way (upstream, not ours)

- `TildagonOSMinimumVersion` capability: store/badge casing mismatch ⇒ silently ignored
  on-badge.
- Pattern apps must export both `__pattern_export__` and `__Pattern_Export__` (casing
  mismatch between PatternDisplay and app store).
- Docs typos: `frontboard.utils` (real: `frontboards.utils`), `TOUCH1` (real: `TOUCH01`),
  `background_update(self)` missing the `delta` param, "2 dps" gyro range claim.
- Official Spaceagon test app calls `eventbus.remove(..., None)` — wrong; pass the app object.

## Remaining unknowns (need hardware or the badge team)

- Exact free-heap ceiling for app installs (tarball + decompression both in RAM).
- Whether `mpremote mount` works with Tildagon OS for live-edit iteration.
- Touch pads: binary only at the Python layer — whether raw capacitance is reachable via
  the C module is unconfirmed.
- Compass calibration: appears raw (no hard-iron cal in firmware) — heading code must
  calibrate.
- Physical clock orientation of TOUCH01–12 vs LED indices (test app draws from an offset of
  −0.42π; verify on hardware).
- Ask in Matrix `#badge:emfcamp.org`: any appetite for store-side monorepo/subdirectory
  support?
