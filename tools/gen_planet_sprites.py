#!/usr/bin/env python3
"""Generate the 12 planetary-button sprites for the Spaceagon touch ring.

The 2026 front plate labels the touch pads with the solar system: Sol at
8 o'clock, then clockwise in sun-outward order (Mercury, Venus, Earth, Mars,
asteroid belt, Jupiter, Saturn, Uranus, Neptune, Kuiper belt, Voyager 1).
One 16x16 pixel-art sprite per pad, drawn by the app at integer-ish scales
with nearest-neighbour, faded out via ctx.global_alpha. Deterministic —
rerun any time; commit the output.

Usage: python tools/gen_planet_sprites.py
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "apps" / "cat_yarn" / "assets" / "planets"

SIZE = 16
CX = CY = 7.5


def blank():
    return Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))


def disc(img, r, pal, cx=CX, cy=CY, bands=None):
    """Shaded circle: outline ring, light from the upper right (like the yarn
    ball). bands maps the integer row offset (y - 8) -> color, overriding the
    shading — pixel rows straddle the half-pixel centre, so index by row."""
    px = img.load()

    def inside(x, y):
        return (x - cx) ** 2 + (y - cy) ** 2 <= r * r

    for y in range(SIZE):
        for x in range(SIZE):
            if not inside(x, y):
                continue
            edge = not all(inside(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if edge:
                px[x, y] = pal["outline"]
            elif bands is not None:
                px[x, y] = bands.get(y - 8, pal["base"])
            else:
                t = (x - cx) * 0.55 - (y - cy) * 0.83
                if t > r * 0.55:
                    px[x, y] = pal["light"]
                elif t < -r * 0.45:
                    px[x, y] = pal["dark"]
                else:
                    px[x, y] = pal["base"]
    return img


def dab(img, pts, color, keep=()):
    """Set pixels, but never overwrite the outline (or transparent gaps when
    the point missed the disc) — features stay inside the silhouette."""
    px = img.load()
    for x, y in pts:
        if 0 <= x < SIZE and 0 <= y < SIZE and px[x, y][3] != 0 and px[x, y] not in keep:
            px[x, y] = color


def sol():
    img = blank()
    pal = {
        "outline": (163, 88, 12, 255),
        "dark": (232, 126, 20, 255),
        "base": (250, 180, 40, 255),
        "light": (255, 220, 90, 255),
    }
    disc(img, 5, pal)
    dab(img, [(7, 6), (8, 6), (7, 7)], (255, 245, 180, 255))
    corona = (255, 160, 30, 255)
    px = img.load()
    rays = [
        (7, 1),
        (8, 1),
        (7, 14),
        (8, 14),
        (1, 7),
        (1, 8),
        (14, 7),
        (14, 8),
        (12, 3),
        (13, 2),
        (3, 3),
        (2, 2),
        (12, 12),
        (13, 13),
        (3, 12),
        (2, 13),
    ]
    for x, y in rays:
        px[x, y] = corona
    return img


def mercury():
    img = blank()
    pal = {
        "outline": (74, 71, 77, 255),
        "dark": (118, 114, 120, 255),
        "base": (158, 152, 158, 255),
        "light": (196, 192, 198, 255),
    }
    disc(img, 3.5, pal)
    dab(img, [(7, 6), (9, 8), (6, 9)], (100, 96, 102, 255), keep=(pal["outline"],))
    return img


def venus():
    img = blank()
    pal = {
        "outline": (138, 94, 38, 255),
        "dark": (198, 142, 72, 255),
        "base": (228, 180, 110, 255),
        "light": (246, 216, 160, 255),
    }
    disc(img, 4.2, pal)
    swirl = (206, 156, 86, 255)
    dab(img, [(5, 6), (6, 5), (8, 5), (9, 6)], swirl, keep=(pal["outline"],))
    dab(img, [(6, 9), (7, 10), (9, 9), (10, 8)], swirl, keep=(pal["outline"],))
    return img


def earth():
    img = blank()
    pal = {
        "outline": (12, 44, 96, 255),
        "dark": (26, 82, 162, 255),
        "base": (40, 120, 210, 255),
        "light": (96, 172, 240, 255),
    }
    disc(img, 4.2, pal)
    land = (60, 160, 80, 255)
    land_dark = (42, 122, 62, 255)
    keep = (pal["outline"],)
    dab(img, [(5, 6), (6, 6), (6, 7), (7, 7), (5, 7)], land, keep=keep)
    dab(img, [(9, 8), (10, 8), (9, 9), (8, 9)], land, keep=keep)
    dab(img, [(6, 10), (7, 10)], land_dark, keep=keep)
    dab(img, [(7, 5), (8, 5)], (235, 245, 250, 255), keep=keep)
    return img


def mars():
    img = blank()
    pal = {
        "outline": (105, 36, 18, 255),
        "dark": (152, 62, 32, 255),
        "base": (200, 90, 50, 255),
        "light": (232, 134, 84, 255),
    }
    disc(img, 4, pal)
    keep = (pal["outline"],)
    dab(img, [(6, 8), (7, 8), (9, 7), (8, 9)], (130, 55, 28, 255), keep=keep)
    dab(img, [(7, 5), (8, 5)], (245, 240, 235, 255), keep=keep)
    return img


def jupiter():
    img = blank()
    cream = (238, 214, 172, 255)
    tan = (198, 148, 96, 255)
    brown = (142, 88, 56, 255)
    pal = {"outline": (95, 60, 35, 255), "dark": tan, "base": cream, "light": cream}
    bands = {
        -7: cream,
        -6: tan,
        -5: cream,
        -4: brown,
        -3: cream,
        -2: tan,
        -1: cream,
        0: tan,
        1: cream,
        2: brown,
        3: cream,
        4: tan,
        5: cream,
        6: cream,
    }
    disc(img, 6.5, pal, bands=bands)
    keep = (pal["outline"],)
    dab(img, [(9, 10), (10, 10), (9, 11)], (200, 80, 50, 255), keep=keep)
    dab(img, [(10, 11)], (160, 55, 35, 255), keep=keep)
    return img


def saturn():
    img = blank()
    pal = {
        "outline": (130, 95, 45, 255),
        "dark": (192, 152, 92, 255),
        "base": (225, 190, 130, 255),
        "light": (245, 220, 170, 255),
    }
    ring = (170, 140, 100, 255)
    ring_front = (240, 220, 180, 255)
    px = img.load()
    rot = math.radians(-24)
    cr, sr = math.cos(rot), math.sin(rot)

    def ring_pixels(front):
        pts = []
        steps = 180
        for i in range(steps):
            t = 2 * math.pi * i / steps
            if (math.sin(t) > 0) != front:
                continue
            dx, dy = 7.0 * math.cos(t), 2.3 * math.sin(t)
            x = int(round(CX + dx * cr - dy * sr))
            y = int(round(CY + dx * sr + dy * cr))
            if 0 <= x < SIZE and 0 <= y < SIZE:
                pts.append((x, y))
        return pts

    for x, y in ring_pixels(front=False):
        px[x, y] = ring
    disc(img, 3.8, pal)
    for x, y in ring_pixels(front=True):
        px[x, y] = ring_front
    return img


def uranus():
    img = blank()
    pal = {
        "outline": (40, 104, 114, 255),
        "dark": (108, 188, 198, 255),
        "base": (150, 220, 225, 255),
        "light": (202, 244, 246, 255),
    }
    disc(img, 4, pal)
    dab(img, [(6, 6), (6, 7), (6, 8)], (128, 202, 210, 255), keep=(pal["outline"],))
    return img


def neptune():
    img = blank()
    pal = {
        "outline": (22, 42, 112, 255),
        "dark": (46, 82, 192, 255),
        "base": (70, 110, 230, 255),
        "light": (132, 172, 250, 255),
    }
    disc(img, 4, pal)
    keep = (pal["outline"],)
    dab(img, [(6, 8), (7, 8)], (30, 60, 160, 255), keep=keep)
    dab(img, [(8, 6), (9, 6)], (176, 205, 252, 255), keep=keep)
    return img


def _rocks(spots, base, dark, light, outline, dust=()):
    img = blank()
    d = ImageDraw.Draw(img)
    for x, y, r in spots:
        d.ellipse((x - r, y - r, x + r, y + r), fill=base, outline=outline)
        img.load()[x, y] = dark
        if r >= 2:
            img.load()[x, y - 1] = light
    for x, y in dust:
        img.load()[x, y] = dark
    return img


def asteroids():
    # A loose diagonal drift of lumpy rocks — the belt, not one body.
    return _rocks(
        [(3, 4, 2), (9, 2, 1), (12, 7, 2), (5, 10, 1), (10, 12, 1)],
        base=(150, 138, 126, 255),
        dark=(96, 88, 80, 255),
        light=(190, 180, 168, 255),
        outline=(70, 62, 56, 255),
        dust=[(7, 7), (14, 3), (2, 13)],
    )


def kuiper():
    # Like the asteroid belt but icy — smaller, colder, more scattered.
    return _rocks(
        [(3, 3, 1), (11, 3, 2), (4, 9, 2), (12, 11, 1), (7, 13, 1)],
        base=(190, 215, 230, 255),
        dark=(120, 150, 175, 255),
        light=(230, 245, 252, 255),
        outline=(80, 105, 130, 255),
        dust=[(8, 6), (14, 7), (1, 12), (7, 1)],
    )


def voyager():
    # Dish up-left, gold bus behind it, magnetometer + RTG booms trailing.
    img = blank()
    d = ImageDraw.Draw(img)
    boom = (140, 150, 160, 255)
    d.line([(9, 9), (14, 12)], fill=boom)
    d.line([(6, 10), (3, 14)], fill=boom)
    d.rectangle((6, 8, 9, 10), fill=(200, 160, 60, 255), outline=(110, 84, 30, 255))
    d.ellipse((3, 1, 11, 7), fill=(226, 232, 238, 255), outline=(60, 70, 80, 255))
    d.ellipse((6, 3, 8, 5), fill=(170, 180, 190, 255))
    img.load()[7, 4] = (60, 70, 80, 255)
    return img


SPRITES = {
    "sol": sol,
    "mercury": mercury,
    "venus": venus,
    "earth": earth,
    "mars": mars,
    "asteroids": asteroids,
    "jupiter": jupiter,
    "saturn": saturn,
    "uranus": uranus,
    "neptune": neptune,
    "kuiper": kuiper,
    "voyager": voyager,
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.png"):
        old.unlink()
    for name, build in sorted(SPRITES.items()):
        img = build()
        img.save(OUT / f"{name}.png", optimize=True)
        print("wrote", OUT / f"{name}.png")


if __name__ == "__main__":
    main()
