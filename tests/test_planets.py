import math

from cat_yarn_planets import (
    HOLD_MS,
    LIFETIME_MS,
    PADS,
    SIZES,
    Flash,
    PlanetField,
)


def test_pads_cover_the_clock():
    assert sorted(PADS) == list(range(1, 13))
    assert len(set(PADS.values())) == 12
    assert set(PADS.values()) == set(SIZES)


def test_pads_walk_the_solar_system_outward_from_sol():
    # Sol is at 8 o'clock; clockwise from there the front plate reads
    # sun-outward — this is what pins Mars (unlabelled in the brief) to pad 12.
    order = [PADS[(7 + i) % 12 + 1] for i in range(12)]
    assert order == [
        "sol",
        "mercury",
        "venus",
        "earth",
        "mars",
        "asteroids",
        "jupiter",
        "saturn",
        "uranus",
        "neptune",
        "kuiper",
        "voyager",
    ]


def test_flash_holds_then_fades_to_nothing():
    f = Flash("mars", 0.0, 0.0)
    assert f.alpha() == 1.0
    f.age = HOLD_MS
    assert f.alpha() == 1.0
    f.age = (HOLD_MS + LIFETIME_MS) // 2
    assert 0.0 < f.alpha() < 1.0
    f.age = LIFETIME_MS
    assert f.alpha() == 0.0


def test_flash_alpha_decreases_monotonically():
    f = Flash("earth", 0.0, 0.0)
    last = 1.0
    for age in range(0, LIFETIME_MS + 1, 250):
        f.age = age
        assert f.alpha() <= last
        last = f.alpha()


def test_spawn_keeps_sprite_inside_radius():
    field = PlanetField()
    seq = [i / 17.0 % 1.0 for i in range(40)]
    rand = lambda: seq.pop(0)  # noqa: E731
    for name in ("sol", "mercury", "jupiter"):
        for _ in range(5):
            flash = field.spawn(name, rand, 111.5)
            limit = 111.5 - SIZES[name] * 0.71
            assert math.hypot(flash.x, flash.y) <= limit + 1e-6


def test_spawn_caps_live_flashes():
    field = PlanetField(max_flashes=3)
    rand = lambda: 0.5  # noqa: E731
    for _ in range(10):
        field.spawn("venus", rand, 100.0)
    assert len(field.flashes) == 3


def test_update_ages_out_flashes_and_reports_activity():
    field = PlanetField()
    assert field.update(100) is False
    field.spawn("neptune", lambda: 0.25, 100.0)
    assert field.update(LIFETIME_MS - 1) is True
    assert field.update(1) is False
    assert field.flashes == []
