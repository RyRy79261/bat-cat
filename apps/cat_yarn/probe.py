"""Dev-only power probe for simulator A/B runs (see tools/power_probe.py).

Activated only when the CATYARN_PROBE env var names a stats file — impossible
on the badge (MicroPython os has no environ), so this module is never even
imported there. It monkeypatches the imu/power fakes to count hardware-access
calls (each one is an I2C transaction on real hardware) and records
update/draw tick counts, dumping JSON once a second.
"""

import json
import math
import os
import time

WIGGLE_ACC = 5.0  # synthetic tilt magnitude, m/s^2 (deadzone is 0.8)
WIGGLE_PERIOD_S = 6.0  # one slow lap of the tilt vector


def _now_s():
    try:
        return time.monotonic()
    except AttributeError:
        return time.ticks_ms() / 1000.0


def _count_calls(mod, name, counts, key):
    orig = getattr(mod, name)

    def wrapped(*args, **kwargs):
        counts[key] += 1
        return orig(*args, **kwargs)

    setattr(mod, name, wrapped)


class Probe:
    def __init__(self, path):
        self.path = path
        self.counts = {
            "imu_reads": 0,
            "battery_level_reads": 0,
            "battery_state_reads": 0,
            "updates": 0,
            "idle_updates": 0,
            "draws": 0,
        }
        self.t0 = _now_s()
        self._last_write = 0.0
        # Optional deterministic tilt stimulus "start:end" (seconds), so A/B
        # runs get an identical idle -> active -> idle trace without a human
        # at the keyboard. Drives the simulator's tilt state directly.
        self._wiggle = None
        self._sim = None
        window = os.environ.get("CATYARN_PROBE_WIGGLE")
        if window:
            start, end = window.split(":")
            self._wiggle = (float(start), float(end))
            try:
                import _sim

                self._sim = _sim._sim
            except ImportError:
                self._wiggle = None
        try:
            import imu

            _count_calls(imu, "acc_read", self.counts, "imu_reads")
        except ImportError:
            pass
        try:
            import power

            _count_calls(power, "BatteryLevel", self.counts, "battery_level_reads")
            _count_calls(power, "BatteryChargeState", self.counts, "battery_state_reads")
        except ImportError:
            pass

    def tick_update(self, idle):
        self.counts["updates"] += 1
        if idle:
            self.counts["idle_updates"] += 1
        now = _now_s()
        if self._wiggle:
            t = now - self.t0
            if self._wiggle[0] <= t < self._wiggle[1]:
                w = 2.0 * math.pi * t / WIGGLE_PERIOD_S
                self._sim.acc = (WIGGLE_ACC * math.cos(w), WIGGLE_ACC * math.sin(w))
            else:
                self._sim.acc = (0.0, 0.0)
        if now - self._last_write >= 1.0:
            self._last_write = now
            self._dump(now)

    def tick_draw(self):
        self.counts["draws"] += 1

    def _dump(self, now):
        data = dict(self.counts)
        data["elapsed_s"] = now - self.t0
        try:
            with open(self.path, "w") as f:
                f.write(json.dumps(data))
        except OSError:
            pass
