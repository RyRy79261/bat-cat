"""Throttled accelerometer polling.

imu.acc_read() is a fresh I2C transaction every call, and the scheduler ticks
update() at ~20 Hz — polling the IMU every tick burns bus + CPU power for
data that (for gravity/tilt use) changes on human timescales. Poll on an
interval instead and serve the cached reading in between, with a slower
interval when the app reports itself idle. interval_ms == 0 disables
throttling (read every update) — used as the A/B baseline.

Reader callable is injectable for tests / the simulator.
"""


def _default_read_acc():
    try:
        import imu

        return imu.acc_read()
    except (ImportError, AttributeError, OSError):
        return (0.0, 0.0, 9.81)


class MotionPoller:
    def __init__(self, read=None, interval_ms=100, idle_interval_ms=400):
        self._read = read or _default_read_acc
        self.interval_ms = interval_ms
        self.idle_interval_ms = idle_interval_ms
        self._acc_ms = 1 << 30  # force an immediate first read
        self.value = (0.0, 0.0, 9.81)
        self.reads = 0

    def update(self, delta_ms, idle=False):
        """Advance by delta_ms and return the freshest allowed reading."""
        interval = self.idle_interval_ms if idle else self.interval_ms
        self._acc_ms += delta_ms
        if self._acc_ms >= interval:
            self._acc_ms = 0
            self.value = self._read()
            self.reads += 1
        return self.value
