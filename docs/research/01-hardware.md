# Hardware: the Spaceagon (EMF 2026) on the Tildagon platform

> Research snapshot: 2026-07-18, verified against `emfcamp/badge-2024-software` @ `beef903`
> (2026-07-16), `emfcamp/badge-2024-documentation` @ `8c0254a` (2026-07-17), and
> `emfcamp/badge-2024-hardware` (BOM/KiCad).

## The one-sentence version

The **Spaceagon is not a new badge** — it's the 2024 hexagonal **Tildagon** base board,
screen, and battery reused, with a new 2026 two-board front assembly (a blue *middleboard*
carrying the screen + a black *frontboard* with the new inputs). Tildagon OS detects which
front board is fitted at boot and starts the matching input stack. Everything is designed as
a multi-year reusable platform; the hexpansion (expansion port) interface is unchanged.

Sources: [EMF blog announcement](https://blog.emfcamp.org/2026/05/28/tildagon-2026-spaceagon/),
[spaceagon-assembly docs](https://github.com/emfcamp/badge-2024-documentation/blob/main/docs/using-the-badge/spaceagon-assembly.md),
[Hackaday](https://hackaday.com/2026/06/02/the-2026-emf-badge-arrives-with-an-add-on-as-expected-its-familiar/).

## Core (base board, unchanged 2024 → 2026)

| Thing | Detail |
|---|---|
| MCU module | Espressif **ESP32-S3-PICO-1-N8R2** — dual-core LX7 @ 240 MHz, **8 MB flash + 2 MB PSRAM** in-package |
| Radio | WiFi 2.4 GHz + BLE (NimBLE compiled into firmware) |
| Display | 1.28" round **GC9A01** SPI LCD, **240×240**, RGB565. SCK=GPIO8, MOSI=GPIO7, CS=GPIO1, DC=GPIO2. No backlight control. |
| LEDs | One WS2812-protocol chain of **19 SK6805 RGB LEDs on GPIO21**. Indices **1–12 = front ring** (clock positions), **13–18 = hexpansion slot backlights**. Power gated via eGPIO `(2,2)` |
| IMU | 6-axis accel+gyro on the system I2C bus — **Bosch BMI270** on production badges (@0x69); prototype badges have an ST LSM6DS3 (@0x6B). Firmware probes BMI270 first, falls back to LSM6DS3; `imu.id()` tells you which |
| PMIC | TI **BQ25895** (I2C 0x6A) — LiPo charge, boost, power-path |
| Battery | 2000 mAh 3.7 V LiPo, JST-PH, max 64×40×7 mm |
| USB | **Two USB-C ports**: "usb in" (device) + "usb out" (host, can power other badges). FUSB302MPX USB-PD PHYs, TS3USB221A mux switching the ESP32-S3's single USB D+/D− (GPIO19/20). USB-PD vendor messages exposed to apps (`pd` module) for badge-to-badge comms |
| Boop button | GPIO0 (also the bootloader strap). "Reboop" = restart |

## What the 2026 Spaceagon front assembly adds

All new parts hang off the front board's own I2C bus (see topology below):

| Input/sensor | Hardware | Notes |
|---|---|---|
| 6 push buttons **A–F** in a row | 4th AW9523B eGPIO expander @ 0x58 on the frontboard, pins (3,8)–(3,13) | Map to UP/RIGHT/CONFIRM/DOWN/LEFT/CANCEL |
| **5-way joystick** (up/down/left/right/fire "nubbin") | Reuses the base-board eGPIO lines the 2024 buttons used | This is why un-updated firmware only sees the joystick |
| **12-pad capacitive touch ring** (TOUCH01–TOUCH12, clock layout, one pad over each ring LED) | Infineon/Cypress **CY8CMBR3116** CapSense controller @ I2C 0x37 | Binary down/up only (no analog exposed to apps) |
| **2 proximity sensors** (LEFTPROX / RIGHTPROX) | Same CY8CMBR3116 | Left/right board edges |
| **Compass / magnetometer** | QST **QMC6309** @ I2C 0x7C, 100 Hz, ±8 gauss | New in 2026 — absent on the 2024 board |
| ID EEPROM | 8 KB Zetta ZD24C64A @ 0x57, hexpansion-style header vid `0xBAD3` pid `0x2600`/`0x2601`, LittleFS mounted at `/frontboard` | How the OS detects the frontboard |

Two frontboard hardware revisions exist (PID `0x2600` and `0x2601`, differing in the JOYLEFT
pin). `detect_frontboard()` returns `0x26XX` for Spaceagon, `0x2400` for the 2024 board.

**Not on the badge at all:** speaker, buzzer, microphone, ambient light sensor, backlight
control. Haptics/GPS exist only as hexpansion-provided "capabilities".

## I2C topology (matters if you ever go below the Python APIs)

One ESP32-S3 I2C master (SDA=GPIO45, SCL=GPIO46) behind a **TCA9548A 8-channel mux @ 0x77**:

- port 0 = **TOP** (front board: buttons expander, touch controller, compass, EEPROM)
- ports 1–6 = the six **hexpansion slots** (each its own isolated `machine.I2C(n)` bus)
- port 7 = **SYSTEM** (PMIC, IMU, the three base-board AW9523B expanders @ 0x58/0x59/0x5A)

## Hexpansion boundary (we're building apps, not these)

Six SFP-style 20-pin edge slots for 1 mm boards, 32 mm across flats. Each slot: 600 mA
current-limited 3.3 V, its own I2C bus, 4 high-speed GPIO (direct ESP32-S3 pins), 5 low-speed
eGPIO (AW9523B, PWM-capable), a detect pin, optional identity EEPROM that can auto-run apps.
Apps can *react* to hexpansions via events — see `04-sensors-and-peripherals.md`.

## 2024 vs 2026 quick diff

| Aspect | Tildagon 2024 | Spaceagon 2026 |
|---|---|---|
| Structure | Single top PCB; screen on header pins (falls off) | Two-board sandwich; screen screwed down, new ribbon |
| Buttons | 6 around the hexagon edges | 6 (A–F) in a row on the frontboard |
| Joystick / touch / prox / compass | — | All new |
| Base board, LEDs, display, hexpansions | Same | Same |

**Firmware ordering caveat:** update Tildagon OS *before* fitting a Spaceagon frontboard —
old firmware only understands the joystick (it sits on the old button lines).

## Open questions

- No public KiCad/CAD for the 2026 frontboard/middleboard exists yet (only 2024 boards in
  `badge-2024-hardware`); there is no `badge-2026-*` hardware repo.
- Exact difference between frontboard revisions 0x2600 / 0x2601 beyond the JOYLEFT pin.

## Key sources

- <https://tildagon.badge.emfcamp.org/tildagon-apps/reference/spaceagon/>
- <https://tildagon.badge.emfcamp.org/tildagon-apps/reference/badge-hardware/>
- <https://github.com/emfcamp/badge-2024-software> — `modules/frontboards/twentysix.py`, `drivers/tildagon_frontboard/`, `drivers/tildagon_imu/qmc6309/`, `drivers/tildagon_i2c/`, `drivers/tildagon_power/`, `drivers/gc9a01/display.c`
- <https://github.com/emfcamp/badge-2024-hardware> — `pins-and-bom.ods` (definitive pin map + BOM)
- <https://github.com/emfcamp/badge-2024-documentation> — `docs/using-the-badge/spaceagon-assembly.md`, `docs/hexpansions/creating-hexpansions.md`
