# Research: ambient power draw — IMU polling, repaint rate, battery monitor

> Snapshot 2026-07-19. Question: is the frequency at which bat-cat touches the motion
> sensor (and repaints) draining the badge battery it's supposed to be ambiently
> monitoring — and is the battery monitor itself part of the problem? Measured with the
> official simulator (`badge-2024-software` @ v2.1.1) via `tools/power_probe.py`.

## TL;DR

- **The battery monitor is innocent.** It polls the PMIC at 1 Hz (the research floor from
  `04-sensors-and-peripherals.md`); turning it off entirely changed CPU cost by 0.2% —
  measurement noise. Keep the ring.
- **The accelerometer polling and the repaint rate were the drain.** The scheduler ticks
  `update()` at ~20 Hz and the app did a fresh `imu.acc_read()` I2C transaction on *every*
  tick — ~1,170 reads/min even with the scene fully settled. The old idle path throttled
  redraws only, never sensor reads.
- Throttling the IMU to 10 Hz active / 2.5 Hz idle and capping active repaints at
  ~12.5 fps cut host CPU time **37%** with no change in behaviour (physics and input still
  run at every tick; only sensor touches and repaints are decimated).

## Method

The simulator has no battery model, so we measure the things that cost power on the badge
and their best off-badge proxy:

- **counts** of hardware accesses (each `imu.acc_read()` / `power.BatteryLevel()` is an
  I2C transaction on real hardware) and of full-screen repaints;
- **host CPU seconds** of the whole simulator process as a proxy for compute cost.

`tools/power_probe.py` vendors the app, boots the official sim headless (SDL dummy
driver), and runs each config for 90 s under an *identical scripted tilt trace*
(10 s settle → 30 s rotating tilt → 50 s settle), injected into the sim's tilt state by
the env-gated `apps/cat_yarn/probe.py`. Counters dump to JSON once a second.

Configs (set via the `spmono_catyarn_*` flags, same build):

| config | imu_ms | imu_idle_ms | draw_ms | battery_ms |
|---|---|---|---|---|
| `baseline` (pre-throttle behaviour) | 0 (every tick) | 0 | 0 (every tick) | 1000 |
| `throttled` (new defaults) | 100 | 400 | 80 | 1000 |
| `no_battery` (isolate the monitor) | 0 | 0 | 0 | never re-read |

## Results (90 s per config, 2026-07-19)

| per minute | baseline | throttled | no_battery |
|---|---:|---:|---:|
| IMU reads | 1,169 | **362 (−69%)** | 1,166 |
| battery reads | 59 | 59 | 0.7 |
| screen repaints | 637 | **360 (−43%)** | 639 |
| update ticks | 1,170 | 1,173 | 1,166 |
| idle ticks | 602 | 602 | 600 |
| **host CPU s / 90 s run** | **26.81** | **16.89 (−37%)** | **26.75 (−0.2%)** |

Reading it:

- Removing the battery monitor (59 → 0.7 reads/min) moved CPU by 0.2% — under run-to-run
  noise. At 1 Hz it is ~5% of the baseline app's I2C traffic and none of its compute.
- The IMU was ~20× the battery monitor's I2C traffic at baseline, and kept transacting at
  full rate while idle (idle ticks ≈ half the trace).
- The CPU saving tracks the repaint reduction most strongly — `ctx` rasterising a full
  240×240 frame is the expensive step, IMU decimation the second-order win (and on real
  hardware each skipped I2C transaction also saves bus power the sim can't see).

## What shipped (new defaults, all flag-overridable)

- `spmono.sensors.motion.MotionPoller` — accelerometer polled at 10 Hz while anything
  moves, 2.5 Hz once settled, cached value served in between (`imu_ms`, `imu_idle_ms`;
  0 = read every tick).
- Active repaint cap ~12.5 fps (`draw_ms=80`), matching the run animation's 80 ms frame
  cadence, so cats don't visibly lose frames. Idle redraw unchanged at 2 Hz
  (`idle_draw_ms=500`). Physics, cat brains and input still run at every ~50 ms tick.
- Battery monitor unchanged at 1 Hz (`battery_ms`).

Latency cost: a tilt that starts while settled is noticed within ≤400 ms (one idle IMU
interval) — acceptable for an ambient toy; nudge/touch input latency is unaffected since
inputs are event-driven and sampled every tick.

## Caveats

- Host CPU time ≠ badge milliamps: the sim rasterises with a different ctx backend, the
  733×733 pygame window adds per-frame overhead, and I2C/display-bus power is invisible
  off-badge. The counts are exact, the CPU percentage is directional.
- The wiggle drives the sim's shared tilt state; run configs one at a time (the harness
  does).
- Repro: `python3.10 tools/power_probe.py cat_yarn` (same env as `just sim`; ~4.5 min).
  Raw output lands in `.cache/probe/results.json`.
