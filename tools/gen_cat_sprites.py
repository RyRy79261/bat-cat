#!/usr/bin/env python3
"""Build the bat-cat sprite frames from the source sheet + generate the yarn.

Cat frames are sliced from tools/assets/cat_sheet.png (32x32 cells, cat facing
right), re-anchored onto 20x20 canvases with a common baseline so animation
frames don't wobble. The yarn ball is generated from a fixed 16x16 silhouette
with 16-bit-style shading. Perch frames (cat sitting/lying on the ball) are
composited from both. Deterministic — rerun any time; commit the output.

Everything is authored at 1x and drawn by the app at 2x (nearest-neighbour),
so one art pixel = two screen pixels across all sprites.

Usage: python tools/gen_cat_sprites.py
"""

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SHEET = ROOT / "tools" / "assets" / "cat_sheet.png"
OUT = ROOT / "apps" / "cat_yarn" / "assets" / "cat" / "default"

CELL = 32
CAT_CANVAS = 20
CAT_BASELINE = 18  # feet rest on this row in every re-anchored frame

# (row, col) cells in the sheet for each output frame.
CAT_FRAMES = {
    "idle0.png": (0, 0),
    "idle1.png": (0, 1),
    "idle2.png": (0, 2),
    "idle3.png": (0, 3),
    "run0.png": (9, 0),
    "run1.png": (9, 1),
    "run2.png": (9, 2),
    "run3.png": (9, 3),
    "run4.png": (9, 4),
    "run5.png": (9, 5),
    "run6.png": (9, 6),
    "run7.png": (9, 7),
    "sleep0.png": (6, 0),
    "sleep1.png": (6, 1),
    "sleep2.png": (6, 2),
    "sleep3.png": (6, 3),
    "fright0.png": (8, 1),  # rearing up, paws out
    "fright1.png": (5, 5),  # landing crouch
    "jump0.png": (8, 2),  # leaping, rising
    "jump1.png": (8, 3),  # leaping, coming down
}

# The yarn ball silhouette (16x16, X = ball).
YARN_MASK = """
OOOOOOOOOOOOOOOO
OOOOOOOXXXOOOOOO
OOOOOOXXXXXOOOOO
OOOOOXXXXXXXXOOO
OOOOXXXXXXXXXXOO
OOOXXXXXXXXXXXXO
OOXXXXXXXXXXXXXX
OOXXXXXXXXXXXXXX
OOXXXXXXXXXXXXXX
OOXXXXXXXXXXXXXX
OOOXXXXXXXXXXXXO
OOOOXXXXXXXXXXOO
OOOOOXXXXXXXXOOO
OOOOOOXXXXXOOOOO
OOOOOOOXXXOOOOOO
OOOOOOOOOOOOOOOO
"""

YARN = {
    "outline": (74, 32, 42, 255),
    "strand": (139, 44, 60, 255),
    "dark": (176, 58, 76, 255),
    "base": (214, 84, 100, 255),
    "light": (238, 140, 150, 255),
    "shine": (250, 194, 198, 255),
}

# Perch composite layout (24x24 canvas): where the yarn ball sits and how deep
# the cat sinks into its top edge.
PERCH_CANVAS = 24
PERCH_YARN_POS = (4, 8)  # yarn 16x16 pasted here -> ball centre ~(12, 16)
PERCH_SIT_FEET = 12  # sitting cat's baseline row (ball top edge is y=9)
PERCH_LIE_FEET = 11  # lying cat drapes across the ball's top


def slice_cat(sheet, row, col):
    cell = sheet.crop((col * CELL, row * CELL, (col + 1) * CELL, (row + 1) * CELL))
    bbox = cell.getbbox()
    art = cell.crop(bbox)
    out = Image.new("RGBA", (CAT_CANVAS, CAT_CANVAS), (0, 0, 0, 0))
    x = (CAT_CANVAS - art.width) // 2
    y = CAT_BASELINE - art.height
    out.paste(art, (x, y), art)
    return out


def yarn_ball():
    rows = [r for r in YARN_MASK.split() if r]
    size = len(rows[0])
    mask = [[ch == "X" for ch in row] for row in rows]

    def inside(x, y):
        return 0 <= x < size and 0 <= y < size and mask[y][x]

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = img.load()
    cx, cy = 8.5, 8.0
    for y in range(size):
        for x in range(size):
            if not mask[y][x]:
                continue
            edge = not all(inside(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if edge:
                px[x, y] = YARN["outline"]
                continue
            # Light from the upper right, shade to the lower left.
            t = (x - cx) * 0.55 - (y - cy) * 0.83
            if t > 3.2:
                px[x, y] = YARN["light"]
            elif t < -2.2:
                px[x, y] = YARN["dark"]
            else:
                px[x, y] = YARN["base"]
    d = ImageDraw.Draw(img)
    # Wrapped strands: curved runs of darker pixels so the ball reads as wound
    # yarn and its rotation is visible when the app spins the sprite.
    d.line([(3, 9), (4, 6), (6, 4), (9, 3), (12, 4)], fill=YARN["strand"])
    d.line([(4, 12), (7, 13), (10, 13), (13, 11)], fill=YARN["strand"])
    d.line([(10, 3), (12, 6), (13, 9), (12, 12)], fill=YARN["strand"])
    d.point((11, 4), fill=YARN["shine"])
    d.point((12, 5), fill=YARN["shine"])
    # Loose thread trailing off the lower right.
    d.point((14, 12), fill=YARN["outline"])
    d.point((15, 13), fill=YARN["strand"])
    d.point((15, 14), fill=YARN["strand"])
    return img


def perch(cat_frame, yarn, feet_y):
    img = Image.new("RGBA", (PERCH_CANVAS, PERCH_CANVAS), (0, 0, 0, 0))
    x = (PERCH_CANVAS - CAT_CANVAS) // 2
    img.paste(cat_frame, (x, feet_y - CAT_BASELINE), cat_frame)
    img.paste(yarn, PERCH_YARN_POS, yarn)  # ball in front occludes the cat's feet
    return img


def main():
    sheet = Image.open(SHEET).convert("RGBA")
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.png"):
        old.unlink()

    frames = {name: slice_cat(sheet, row, col) for name, (row, col) in CAT_FRAMES.items()}
    yarn = yarn_ball()
    frames["yarn.png"] = yarn
    frames["perch_sit0.png"] = perch(frames["idle0.png"], yarn, PERCH_SIT_FEET)
    frames["perch_sit1.png"] = perch(frames["idle1.png"], yarn, PERCH_SIT_FEET)
    frames["perch_lie0.png"] = perch(frames["sleep0.png"], yarn, PERCH_LIE_FEET)
    frames["perch_lie1.png"] = perch(frames["sleep1.png"], yarn, PERCH_LIE_FEET)

    for name, img in sorted(frames.items()):
        img.save(OUT / name, optimize=True)
        print("wrote", OUT / name)


if __name__ == "__main__":
    main()
