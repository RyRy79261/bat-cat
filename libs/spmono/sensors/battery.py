"""Smoothed battery monitoring.

power.BatteryLevel() performs a fresh PMIC I2C read on every call and the
discharging value is a noisy linear voltage map — so poll at >= 1 s intervals
and EMA-smooth. The level also jumps discontinuously when charging starts or
stops; expose charge state so UIs can switch display mode instead.

Reader callables are injectable for tests / the simulator.
"""


def _default_read_level():
    try:
        import power

        level = power.BatteryLevel()
        if level < 0.0:
            return 0.0
        if level > 100.0:
            return 100.0
        return level
    except (ImportError, AttributeError, OSError):
        return 75.0


def _default_read_state():
    try:
        import power

        return power.BatteryChargeState()
    except (ImportError, AttributeError, OSError):
        return "Not Charging"


class BatteryMonitor:
    def __init__(self, read_level=None, read_state=None, interval_ms=1000, alpha=0.25):
        self._read_level = read_level or _default_read_level
        self._read_state = read_state or _default_read_state
        self.interval_ms = interval_ms
        self.alpha = alpha
        self._acc = interval_ms  # force an immediate first read
        self.level = None
        self.state = "Not Charging"

    @property
    def charging(self):
        return self.state in ("Pre-Charging", "Fast Charging")

    def update(self, delta_ms):
        self._acc += delta_ms
        if self._acc < self.interval_ms:
            return
        self._acc = 0
        raw = self._read_level()
        old_state = self.state
        self.state = self._read_state()
        if self.level is None or old_state != self.state:
            self.level = raw  # snap on first read and across charge transitions
        else:
            self.level += self.alpha * (raw - self.level)
