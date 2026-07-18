# Sensors & peripherals — how apps address the hardware

> Research snapshot: 2026-07-18, verified against firmware source
> (`emfcamp/badge-2024-software` @ `beef903`) and docs source (@ `8c0254a`).

## IMU: accelerometer / gyro / steps — `import imu` (C module, module-level functions)

| Function | Returns | Units |
|---|---|---|
| `imu.acc_read()` | `(x, y, z)` floats | m/s² |
| `imu.gyro_read()` | `(x, y, z)` floats | degrees/second |
| `imu.mag_read()` | `(x, y, z)` floats | gauss — **2026 frontboard only** |
| `imu.step_counter_read()` / `step_counter_reset()` | int / None | steps |
| `imu.temperature_read()` | float | °C |
| `imu.id()` | `"bmi270"` or `"lsm6ds3"` | which chip this badge has |
| `imu.readfrom(reg, len)` / `writeto(reg, buf)` | raw register access | — |

The firmware supports two IMU chips behind one API: it probes the **BMI270** (production
badges, @0x69) first and falls back to the **LSM6DS3** (prototype badges, @0x6B). `imu.id()`
returns `"bmi270"`, `"lsm6ds3"`, or `"no device present"` — **check it rather than assuming**.

## Compass (2026) — `imu.mag_read()`

- Chip: QST QMC6309 @ I2C 0x7C on the frontboard bus; continuous mode, 100 Hz, ±8 gauss.
- Registered only when the 2026 frontboard init succeeds. **On a 2024 board it silently
  returns stale/zero values — it does not raise.** Guard with `detect_frontboard()`.
- Values appear to be raw (no hard-iron calibration in firmware) — a heading feature in our
  common library should include its own calibration routine.

## LEDs — `from tildagonos import tildagonos`

```python
from tildagonos import tildagonos
from system.eventbus import eventbus
from system.patterndisplay.events import PatternDisable, PatternEnable

eventbus.emit(PatternDisable())          # stop the default LED pattern first
tildagonos.leds[1] = (255, 0, 0)         # indices 1-12: front ring (clock positions)
tildagonos.leds[13] = (0, 0, 255)        # indices 13-18: hexpansion slot backlights
tildagonos.leds.write()                  # commit
# on exit: eventbus.emit(PatternEnable())  — known community gotcha: reset LEDs on exit!
```

- 19-LED WS2812 chain on GPIO21; RGB ints 0–255.
- `tildagonos.set_led_power(True)` enables the rail (needed from REPL; apps usually fine).
- No global brightness API; the system pattern uses the `pattern_brightness` setting (0.1–1.0).
- `PatternSet(PatternClass)` / `PatternReload()` for swapping patterns programmatically.

## Power / battery — `import power` (C module)

`power.BatteryLevel()` (percent float), `Vbat()`, `Vin()`, `Vsys()`, `Icharge()` (A),
`BatteryChargeState()` → `"Not Charging" | "Pre-Charging" | "Fast Charging" | "Terminated"`,
`Fault()`, `SupplyCapabilities()`, `Enable5V(bool)`, `Off()`.

USB attach/detach and charge states also arrive as events (`system.power.events`):
`RequestHostAttachEvent/DetachEvent`, `RequestDeviceAttachEvent/DetachEvent`,
`RequestChargeEvent`, fault events, and badge-to-badge PD events. USB-PD messaging between
badges: `from pd import Host, Device` (`send_vendor_msg`, `badge_connected()`, …).

## Display & backlight

Drawing is only via `ctx` in `draw()` (see `02-app-model.md`). There is **no backlight
control** (BSP compiles with `backlight_used = 0`) and no ambient light sensor.

## Radio: WiFi / BLE / ESP-NOW

- **WiFi** — `import wifi`: `connect(ssid=None, password=None, username=None)` (supports
  WPA2-Enterprise), `disconnect()`, `status()`, `wait()`, `scan()`, `get_ip()`, `get_ssid()`,
  `accesspoint_start(ssid, password=None)` + status/stop, `ifconfig()`, `save_defaults(...)`.
  Frozen HTTP client: `requests` (`requests.get(...)`). Also frozen: `umqtt.simple`,
  `umqtt.robust`.
- **BLE** — NimBLE compiled in, `aioble` + `bluetooth` importable. No official docs page;
  community apps (badgemon, space-scanner) prove it works — space-scanner uses connectionless
  `gap_advertise`/`gap_scan` (needs firmware ≥ v2.0.0-alpha.3).
- **ESP-NOW** — frozen `aioespnow` plus a system service:
  `from system.espnow import espnow_service, EspNowReceiveEvent, BROADCAST_MAC`. Docs example:
  `docs/tildagon-apps/examples/inter-badge-communications.md`. Used by tildenstein and
  MusicJam for badge-to-badge multiplayer.

## Time

Plain MicroPython: `ntptime.settime()` after WiFi connect (what the OTA service does), then
`time` / `machine.RTC`. No badge-specific time API.

## Audio / haptics

No speaker, buzzer, or mic on the badge. Haptics exist only as a **capability** provided by
some hexpansions — request with
`eventbus.emit(CustomEvent(type="haptic", params={"effect": "buzz", "strength": 1.0}))`
(effects: click, double_click, buzz, tick, ramp_*, continuous/hum).

## Hexpansions, from an app's point of view

Events (`from system.hexpansion.events import ...`): `HexpansionInsertionEvent(port)`,
`HexpansionRemovalEvent(port)`, `HexpansionMountedEvent(port, header)`,
`HexpansionUnmountedEvent(port, header)`, plus formatted/app-launch events. Find hardware:
`system.hexpansion.util.get_slots_by_vid_pid(vid, pid)`; access it via
`HexpansionConfig(port)` → `.i2c`, `.pin[]` (high-speed `machine.Pin`), `.ls_pin[]` (eGPIO
with `.duty()` PWM). Per-slot I2C buses are `machine.I2C(1)`…`I2C(6)`.

Manifest-level: declare `[[metadata.capabilities]]` with a hexpansion `{vid, pid}` or
`{ type = "2026 Frontboard" }` if your app needs one — see `06-publishing.md`.

## Key sources

- <https://tildagon.badge.emfcamp.org/tildagon-apps/reference/badge-hardware/>
- Firmware: `drivers/tildagon_imu/` (incl. `qmc6309/`), `drivers/tildagon_power/mp_power.c`,
  `modules/tildagonos.py`, `modules/wifi.py`, `modules/system/espnow/`,
  `modules/system/hexpansion/`, `modules/system/patterndisplay/`, `tildagon/manifest.py`
  in <https://github.com/emfcamp/badge-2024-software>
- Haptic capability spec: `docs/capabilities/registry/haptic-feedback.md` in the docs repo
