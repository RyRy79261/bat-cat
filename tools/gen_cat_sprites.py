#!/usr/bin/env python3
"""Generate the Cat & Yarn pixel-art sprite frames (24x24 PNGs, cat 19px tall
incl. tail). Deterministic — rerun any time; commit the output.

Usage: python tools/gen_cat_sprites.py [--skin default]
"""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 24

SKINS = {
    "default": {
        "body": (150, 156, 168, 255),
        "dark": (72, 76, 86, 255),
        "belly": (208, 212, 220, 255),
        "pink": (232, 130, 150, 255),
        "eye": (46, 200, 120, 255),
    },
    "void": {
        "body": (28, 28, 34, 255),
        "dark": (10, 10, 14, 255),
        "belly": (60, 60, 70, 255),
        "pink": (200, 90, 120, 255),
        "eye": (250, 210, 60, 255),
    },
}


def _canvas():
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def _ears(d, c, tips, back=False):
    # tips: [(x, y), (x, y)] ear tip pixels; ears drawn as small triangles
    for tx, ty in tips:
        d.polygon([(tx - 2, ty + 3), (tx + 1, ty + 3), (tx, ty)], fill=c["dark"])


def idle(c, tail_up):
    img, d = _canvas()
    # 19px tall budget: y=5..23 (head top 6, ground 23)
    d.ellipse((6, 12, 18, 23), fill=c["body"], outline=c["dark"])  # seated body
    d.ellipse((11, 6, 21, 15), fill=c["body"], outline=c["dark"])  # head
    _ears(d, c, [(13, 4), (19, 4)])
    d.point((18, 10), fill=c["eye"])
    d.point((21, 11), fill=c["pink"])  # nose
    d.line((15, 17, 15, 22), fill=c["dark"])  # front leg hint
    if tail_up:
        d.line((6, 18, 3, 12), fill=c["dark"], width=2)
        d.point((3, 11), fill=c["body"])
    else:
        d.line((6, 21, 1, 22), fill=c["dark"], width=2)
    return img


def run(c, pose):
    img, d = _canvas()
    d.ellipse((3, 11, 18, 19), fill=c["body"], outline=c["dark"])  # stretched body
    d.ellipse((13, 5, 22, 14), fill=c["body"], outline=c["dark"])  # head
    _ears(d, c, [(15, 3), (20, 3)])
    d.point((19, 9), fill=c["eye"])
    d.point((22, 10), fill=c["pink"])
    d.line((3, 12, 0, 8), fill=c["dark"], width=1)  # tail streaming behind
    if pose == 0:  # stretch: legs extended fore and aft
        d.line((16, 18, 21, 22), fill=c["dark"], width=2)
        d.line((5, 18, 1, 22), fill=c["dark"], width=2)
    elif pose == 1:  # gather: legs tucked under
        d.line((14, 18, 12, 22), fill=c["dark"], width=2)
        d.line((8, 18, 9, 22), fill=c["dark"], width=2)
    else:  # mid-stride
        d.line((15, 18, 18, 22), fill=c["dark"], width=2)
        d.line((6, 18, 4, 22), fill=c["dark"], width=2)
    return img


def fright_air(c):
    img, d = _canvas()
    d.ellipse((1, 5, 7, 11), fill=c["body"], outline=c["dark"])  # puffed tail (attached)
    d.ellipse((5, 8, 17, 16), fill=c["body"], outline=c["dark"])  # arched body
    d.ellipse((12, 3, 21, 11), fill=c["body"], outline=c["dark"])  # head up
    _ears(d, c, [(14, 1), (19, 1)])
    d.rectangle((17, 6, 18, 7), fill=c["eye"])  # wide eye
    d.point((21, 8), fill=c["pink"])
    for x in (6, 9, 13, 16):  # splayed legs
        d.line((x, 15, x - 1, 20), fill=c["dark"], width=1)
    return img


def fright_land(c):
    img, d = _canvas()
    d.ellipse((4, 15, 19, 23), fill=c["body"], outline=c["dark"])  # flat crouch
    d.ellipse((13, 10, 22, 18), fill=c["body"], outline=c["dark"])  # head low
    _ears(d, c, [(15, 8), (20, 8)])
    d.point((19, 13), fill=c["eye"])
    d.point((22, 14), fill=c["pink"])
    d.line((4, 17, 1, 13), fill=c["dark"], width=2)  # tail still up
    return img


def sleep(c):
    img, d = _canvas()
    d.ellipse((5, 10, 20, 23), fill=c["body"], outline=c["dark"])  # curled loaf
    _ears(d, c, [(15, 8), (19, 8)])  # ear nubs so the loaf reads as cat
    d.ellipse((7, 13, 14, 20), fill=c["belly"])  # curl highlight
    d.line((15, 15, 17, 15), fill=c["dark"])  # closed eye
    d.arc((3, 14, 12, 23), 90, 250, fill=c["dark"], width=2)  # wrapped tail
    return img


def build(skin):
    c = SKINS[skin]
    return {
        "idle0.png": idle(c, False),
        "idle1.png": idle(c, True),
        "run0.png": run(c, 0),
        "run1.png": run(c, 1),
        "run2.png": run(c, 2),
        "fright0.png": fright_air(c),
        "fright1.png": fright_land(c),
        "sleep0.png": sleep(c),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skin", default="default", choices=sorted(SKINS))
    args = parser.parse_args()
    out = (
        Path(__file__).resolve().parent.parent / "apps" / "cat_yarn" / "assets" / "cat" / args.skin
    )
    out.mkdir(parents=True, exist_ok=True)
    for name, img in build(args.skin).items():
        img.save(out / name, optimize=True)
        print("wrote", out / name)


if __name__ == "__main__":
    main()
