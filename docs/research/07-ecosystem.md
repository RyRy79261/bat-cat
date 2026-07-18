# Ecosystem: repos to learn from, community, prior art

> Research snapshot: 2026-07-18. ~175 public repos carry the `tildagon-app` GitHub topic
> (which IS the app directory's data source). All repos below were verified on GitHub;
> "Jul 2026" = released/updated around or after EMF 2026.

## The must-read repos

| Repo | Why it matters |
|---|---|
| [emfcamp/badge-2026-apps-spaceagon-test](https://github.com/emfcamp/badge-2026-apps-spaceagon-test) | **The canonical 2026 example** (official frontboard test app, v0.0.3 Jul 2026). Exercises every new input: `frontboards.twentysix` TOUCH/PROX, `JOYSTICK_BUTTON_TYPES`, `imu.mag_read()`, manual C+D chord. Install on-badge with code `21230442`. |
| [emfcamp/badge-2024-software](https://github.com/emfcamp/badge-2024-software) | Tildagon OS itself + the simulator (`sim/`). The real API reference when docs lag. v2.1.1, Jul 2026. |
| [emfcamp/badge-2024-documentation](https://github.com/emfcamp/badge-2024-documentation) | Source of tildagon.badge.emfcamp.org. Read the markdown directly. |
| [emfcamp/badge-2024-app-store](https://github.com/emfcamp/badge-2024-app-store) | App directory backend — the ground truth on publishing mechanics. |
| [hughrawlinson/tildagon-demo](https://github.com/hughrawlinson/tildagon-demo) | The official "fork this" template (57 forks). Minimal app.py + tildagon.toml. |

## Best community apps to steal patterns from (all active Jul 2026)

| Repo | Pattern it demonstrates |
|---|---|
| [webboggles/tildenstein](https://github.com/webboggles/tildenstein) | Raycasting FPS: **ESP-NOW mesh multiplayer**, IMU tilt controls, LED "peer radar", performance-focused rendering. Multi-module (`engine.py`, `net.py`, …). |
| [analogue-stick/badgemon](https://github.com/analogue-stick/badgemon) | Big well-factored app: `game/`, `scenes/`, `assets/`, `protocol/`, `util/` packages; **BLE badge-to-badge battles**; prototyped on Pico W first. |
| [dfourn/space-scanner](https://github.com/dfourn/space-scanner) | 2026-era **connectionless BLE** (`gap_advertise`/`gap_scan`, needs fw ≥2.0.0-alpha.3), deterministic procgen, flash persistence, **power-state dimming**, UDP-loopback **desktop test harness**, testable module layout. |
| [area/racecondition](https://github.com/area/racecondition) | One published repo containing badge app + Python **game server** + `tests/` — proof extra dirs alongside root `app.py` are store-compatible. |
| [ntflix/Tildagon-MusicJam](https://github.com/ntflix/Tildagon-MusicJam) | Collaborative synth over ESP-NOW, MIDI events, ~27 modules. |
| [TeamRobotmad/BadgeBot](https://github.com/TeamRobotmad/BadgeBot) | Hexpansion integration (HexDrive motors), **build tooling**: minified `.mpy`, build flavours, dev scripts. |
| [npentrel/tildagon-snake](https://github.com/npentrel/tildagon-snake) + [-imu](https://github.com/npentrel/tildagon-snake-imu) | The docs tutorial lineage; minimal app + IMU-controlled variant (by a docs maintainer). |
| [MatthewWilkes/advanced-leds](https://github.com/MatthewWilkes/advanced-leds) | Closest thing to a community shared library distributed via the store. |
| [andypiper/emf-duckfacts-tildagon](https://github.com/andypiper/emf-duckfacts-tildagon) | (Archived) notable dev workflow: **uv**, Justfile, asset-encoding build scripts, offline-first + WiFi fetch. |
| [Davermouse/hexbadge](https://github.com/Davermouse/hexbadge) | Template-fork example; commit history documents the "reset LEDs on exit" gotcha. |

Nobody was found publishing **multiple apps from one monorepo** — orgs with several apps
(eehackspace, TeamRobotmad) use one repo per app. Our mirror-repo pipeline would be new
ground (see `06-publishing.md`).

No third-party apps confirmed using joystick/touch/compass yet beyond the official test app
— being early to 2026 features is an opportunity. (Grep candidates: any Jul-2026 repo, for
`frontboards.twentysix` / `mag_read`.)

## Community

- Matrix: **#badge:emfcamp.org** (the badge team hangs out here — right place for questions
  like "will the store ever support monorepos?")
- IRC: `#emfcamp-badge` on irc.libera.chat
- Email: badge@emfcamp.org
- No Discord; no awesome-tildagon list exists (searched).

## Prior art worth a glance (briefly)

- The badge's own lineage: Tildagon OS borrows `st3m`/`flow3r_bsp`/`ctx` from the CCC
  **flow3r** badge — flow3r app patterns sometimes translate.
- badgemon's "prototype on a Pico W first" and space-scanner's UDP-loopback desktop harness
  are the two best portable-dev tricks seen in the wild.
