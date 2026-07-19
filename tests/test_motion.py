from spmono.sensors.motion import MotionPoller


def _counting_reader(calls):
    def read():
        calls.append(1)
        return (0.0, float(len(calls)), 9.81)

    return read


def test_first_update_reads_immediately():
    calls = []
    poller = MotionPoller(read=_counting_reader(calls), interval_ms=100)
    value = poller.update(0)
    assert len(calls) == 1
    assert value == (0.0, 1.0, 9.81)


def test_caches_between_intervals():
    calls = []
    poller = MotionPoller(read=_counting_reader(calls), interval_ms=100)
    poller.update(0)
    poller.update(50)  # under the interval — served from cache
    assert len(calls) == 1
    assert poller.update(50) == (0.0, 2.0, 9.81)  # crosses 100 ms
    assert len(calls) == 2


def test_idle_interval_is_slower():
    calls = []
    poller = MotionPoller(read=_counting_reader(calls), interval_ms=100, idle_interval_ms=400)
    poller.update(0, idle=True)
    for _ in range(7):
        poller.update(50, idle=True)  # 350 ms — under the idle interval
    assert len(calls) == 1
    poller.update(50, idle=True)  # crosses 400 ms
    assert len(calls) == 2


def test_zero_interval_reads_every_tick():
    calls = []
    poller = MotionPoller(read=_counting_reader(calls), interval_ms=0)
    for _ in range(5):
        poller.update(50)
    assert len(calls) == 5


def test_fallback_reader_off_badge():
    poller = MotionPoller(interval_ms=0)
    x, y, z = poller.update(0)
    assert z > 9.0  # gravity-shaped default with no imu module present
