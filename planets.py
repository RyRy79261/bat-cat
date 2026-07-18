"""Planetary touch-ring buttons: pad map + the flash lifecycle (pure logic).

The Spaceagon front plate labels the 12 touch pads with the solar system.
Sol sits at 8 o'clock and the system walks clockwise in sun-outward order, so
pad 1 (just after 12:00) is the asteroid belt and pad 12 (just before) is
Mars. Pressing a pad flashes that body somewhere random on screen: fully
visible briefly, then fading to nothing HOLD_MS..LIFETIME_MS after spawn.

No firmware imports — testable on plain CPython. Randomness is injected as a
rand() -> [0, 1) callable.
"""

import math

LIFETIME_MS = 5000
HOLD_MS = 800  # fully opaque this long before the fade begins
MAX_FLASHES = 8

# Touch pad number (clock position, TOUCH01 = 1 o'clock) -> body.
PADS = {
    1: "asteroids",
    2: "jupiter",
    3: "saturn",
    4: "uranus",
    5: "neptune",
    6: "kuiper",
    7: "voyager",
    8: "sol",
    9: "mercury",
    10: "venus",
    11: "earth",
    12: "mars",
}

# On-screen sprite size (px) per body — 16x16 art, nearest-neighbour scaled.
SIZES = {
    "sol": 64,
    "mercury": 28,
    "venus": 40,
    "earth": 44,
    "mars": 36,
    "asteroids": 56,
    "jupiter": 64,
    "saturn": 64,
    "uranus": 44,
    "neptune": 44,
    "kuiper": 56,
    "voyager": 36,
}


class Flash:
    def __init__(self, name, x, y):
        self.name = name
        self.x = x
        self.y = y
        self.age = 0

    def alpha(self):
        if self.age <= HOLD_MS:
            return 1.0
        if self.age >= LIFETIME_MS:
            return 0.0
        return 1.0 - (self.age - HOLD_MS) / float(LIFETIME_MS - HOLD_MS)


class PlanetField:
    """The set of live flashes. update() ages them out; spawn() adds one at a
    random spot that keeps the sprite fully inside the given radius."""

    def __init__(self, max_flashes=MAX_FLASHES):
        self.max_flashes = max_flashes
        self.flashes = []

    def spawn(self, name, rand, fit_radius):
        size = SIZES[name]
        max_r = fit_radius - size * 0.71  # half-diagonal keeps corners inside
        if max_r < 0.0:
            max_r = 0.0
        r = max_r * math.sqrt(rand())  # sqrt -> uniform over the disc
        angle = 2.0 * math.pi * rand()
        flash = Flash(name, r * math.cos(angle), r * math.sin(angle))
        self.flashes.append(flash)
        if len(self.flashes) > self.max_flashes:
            self.flashes.pop(0)
        return flash

    def update(self, delta_ms):
        """Age the flashes; returns True while any are still visible."""
        alive = []
        for flash in self.flashes:
            flash.age += delta_ms
            if flash.age < LIFETIME_MS:
                alive.append(flash)
        self.flashes = alive
        return bool(alive)
