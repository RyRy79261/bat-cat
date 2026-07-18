from spmono import theme
from spmono.sensors.battery import BatteryMonitor


def test_first_read_snaps_then_smooths():
    readings = iter([80.0, 40.0, 40.0, 40.0])
    mon = BatteryMonitor(
        read_level=lambda: next(readings),
        read_state=lambda: "Not Charging",
        interval_ms=1000,
        alpha=0.5,
    )
    mon.update(0)
    assert mon.level == 80.0  # first read snaps
    mon.update(1000)
    assert 55.0 < mon.level < 65.0  # EMA, not a jump to 40


def test_polls_at_interval_not_per_tick():
    calls = []
    mon = BatteryMonitor(
        read_level=lambda: calls.append(1) or 50.0,
        read_state=lambda: "Not Charging",
        interval_ms=1000,
    )
    mon.update(0)
    for _ in range(19):
        mon.update(50)  # 950ms total — under the interval
    assert len(calls) == 1
    mon.update(50)  # crosses 1000ms
    assert len(calls) == 2


def test_charge_transition_snaps_level():
    state = {"s": "Not Charging"}
    level = {"v": 40.0}
    mon = BatteryMonitor(
        read_level=lambda: level["v"],
        read_state=lambda: state["s"],
        interval_ms=1000,
        alpha=0.1,
    )
    mon.update(0)
    state["s"] = "Fast Charging"
    level["v"] = 90.0
    mon.update(1000)
    assert mon.level == 90.0  # snapped, not smoothed across the discontinuity
    assert mon.charging


def test_battery_color_bands():
    th = theme.THEMES["spaceagon"]
    assert theme.battery_color(100.0, th) == th["floor_ok"]
    assert theme.battery_color(0.0, th) == th["floor_low"]
    mid = theme.battery_color(42.0, th)
    assert mid != th["floor_ok"] and mid != th["floor_low"]
