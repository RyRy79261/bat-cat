"""bat-cat — ambient toy for the EMF Spaceagon/Tildagon badge.

The screen's rim is the floor: a thin ring color-coded by battery level. A
ball of yarn and the cats that chase it live ON that floor — beads on the rim
circle, sliding around it under real gravity (accelerometer) and drawn
feet-outward, so nothing ever leaves the floor or hangs upside down. Cats leap
over the ball when it rolls at them, startle when it reverses past them, and
sit (then lie) on top of it when they catch it still. Leave it running; put
the app's menu name in /autoexec.bat to boot straight into it.
"""

import math
import random


def _find_root():
    # Locate this app's install folder for absolute asset paths. NEVER put the
    # app dir on sys.path — its app.py would shadow the firmware's app module.
    try:
        return "/".join(__file__.replace("\\", "/").split("/")[:-1])
    except NameError:
        try:
            import os

            for entry in os.listdir("/apps"):
                # Sideloaded folder is cat_yarn; store installs land in
                # /apps/<owner>_<repo>/ (repo: bat-cat).
                if "cat_yarn" in entry or "bat-cat" in entry or "bat_cat" in entry:
                    return "/apps/" + entry
        except OSError:
            pass
    return "/apps/cat_yarn"


_APP_ROOT = _find_root()

from .cats import CHASE, FRIGHT, JUMP, PERCH, Cat, separate
from .planets import PADS, SIZES, PlanetField
from .spmono import flags, theme
from .spmono.engine.physics import RimBall
from .spmono.engine.sprite import Sprite
from .spmono.sensors.battery import BatteryMonitor
from .spmono.ui.baseapp import BaseApp

try:
    from ._build import DEBUG as _BUILD_DEBUG
except ImportError:
    _BUILD_DEBUG = True  # running from source = dev build

import imu

try:
    from system.eventbus import eventbus
    from system.patterndisplay.events import PatternDisable, PatternEnable
except ImportError:
    eventbus = None

APP = "catyarn"
HALF_PI = math.pi / 2

SCREEN_R = 120
RING_R = 114
RING_W = 5
FLOOR_R = RING_R - RING_W / 2  # inner edge of the floor ring

# Art is authored at 1x; the yarn (14px ball) draws at ~4.25x for 25% of the
# 240px screen, cats (12px sitting) at 4x for 20%.
BALL_R = 30  # yarn ball's visual radius on screen
YARN_SIZE = 68  # 16x16 art at 4.25x
CAT_SIZE = 80  # 20x20 art at 4x
PERCH_SIZE = 102  # 24x24 art at 4.25x
CAT_FEET = 32  # feet baseline sits this far below the sprite centre
PERCH_OFF = (-2, -17)  # composite offset aligning its ball with the real one

BALL_TRACK_R = FLOOR_R - BALL_R
CAT_TRACK_R = FLOOR_R - CAT_FEET

IDLE_REDRAW_MS = 500


def _rand():
    # random.random() is not guaranteed on every MicroPython port; getrandbits is.
    return random.getrandbits(16) / 65536.0


_FRAMES = {
    "idle": [(f"cat/default/idle{i}.png", 400) for i in range(4)],
    "run": [(f"cat/default/run{i}.png", 80) for i in range(8)],
    "sleep": [(f"cat/default/sleep{i}.png", 700) for i in range(4)],
    "fright_up": [("cat/default/fright0.png", 1000)],
    "fright_down": [("cat/default/fright1.png", 1000)],
    "jump_up": [("cat/default/jump0.png", 1000)],
    "jump_down": [("cat/default/jump1.png", 1000)],
    "perch_sit": [("cat/default/perch_sit0.png", 600), ("cat/default/perch_sit1.png", 600)],
    "perch_lie": [("cat/default/perch_lie0.png", 900), ("cat/default/perch_lie1.png", 900)],
}
_YARN = "cat/default/yarn.png"


def _abs_frames(root):
    out = {}
    base = (root or "/apps/cat_yarn") + "/assets/"
    for name, frames in _FRAMES.items():
        out[name] = [(base + path, dur) for path, dur in frames]
    return out


class CatYarnApp(BaseApp):
    def __init__(self):
        super().__init__()
        self.debug = bool(flags.get(APP, "debug_overlay", _BUILD_DEBUG))
        self.ball = RimBall(BALL_R, BALL_TRACK_R)
        self.battery = BatteryMonitor()
        self.yarn_path = (_APP_ROOT or "/apps/cat_yarn") + "/assets/" + _YARN
        self.planet_root = (_APP_ROOT or "/apps/cat_yarn") + "/assets/planets/"
        self.planets = PlanetField()

        n = flags.get(APP, "max_cats", 2)
        n = 1 if n < 1 else (3 if n > 3 else n)
        anims = _abs_frames(_APP_ROOT)
        self.cats = []
        self.sprites = []
        for i in range(n):
            cat = Cat(HALF_PI + (i + 1) * 2.1, track_radius=CAT_TRACK_R)
            self.cats.append(cat)
            self.sprites.append(Sprite(anims, "idle"))

        self._t = 0
        self._idle_acc = 0
        self._prewarmed = False
        self._patterns_off = False
        self._nudge = bool(flags.get(APP, "nudge", True))

    # -- lifecycle -------------------------------------------------------

    def _set_patterns(self, off):
        if eventbus is None:
            return
        if off and not self._patterns_off:
            eventbus.emit(PatternDisable())
            self._patterns_off = True
        elif not off and self._patterns_off:
            eventbus.emit(PatternEnable())
            self._patterns_off = False

    def on_minimise(self):
        self._set_patterns(False)  # community gotcha: restore LEDs on exit

    # -- update ----------------------------------------------------------

    def on_update(self, delta):
        if flags.get(APP, "leds_off", True):
            self._set_patterns(True)
        self._t += delta
        self.battery.update(delta)

        acc = imu.acc_read()
        # Verified mapping: acc[1] -> screen x, acc[0] -> screen y, no flips.
        dt = delta / 1000.0
        self.ball.step(acc[1], acc[0], dt)

        if self._nudge and self.inputs.pressed("nudge"):
            self.ball.v += 90.0 if self.ball.v >= 0.0 else -90.0

        for pad, name in PADS.items():
            if self.inputs.pressed(f"planet_{pad}"):
                self.planets.spawn(name, _rand, FLOOR_R)
        planets_active = self.planets.update(delta)

        perched = None
        for i, cat in enumerate(self.cats):
            if cat.state == PERCH:
                perched = i
                break

        active = planets_active or self.ball.speed() > 2.0
        for i, (cat, sprite) in enumerate(zip(self.cats, self.sprites)):
            cat.update(
                delta,
                self.ball,
                gx=acc[1],
                gy=acc[0],
                can_perch=(perched is None or perched == i),
            )
            if cat.state == PERCH and perched is None:
                perched = i  # claimed this frame — lock the others out
            sprite.set_anim(cat.anim())
            sprite.update(delta)
            if cat.state in (CHASE, FRIGHT, JUMP):
                active = True
        separate(self.cats)

        if active or self.battery.charging:
            self._idle_acc = 0
            return True
        # Ambient idle: everything is settled — redraw slowly to save power.
        self._idle_acc += delta
        if self._idle_acc >= IDLE_REDRAW_MS:
            self._idle_acc = 0
            return True
        return False

    # -- draw ------------------------------------------------------------

    def on_draw(self, ctx):
        th = self.theme

        if not self._prewarmed:
            # Decode every sprite frame once, under the background fill,
            # so there's no mid-chase stutter on first use.
            ctx.image_smoothing = 0
            for path in self.sprites[0].all_paths():
                ctx.image(path, -12, -12, 24, 24)
            ctx.image(self.yarn_path, -12, -12, 24, 24)
            self._prewarmed = True

        bg = th["background"]
        ctx.rgb(bg[0], bg[1], bg[2]).rectangle(-120, -120, 240, 240).fill()

        self._draw_floor(ctx, th)
        self._draw_planets(ctx)
        if not any(cat.state == PERCH for cat in self.cats):
            self._draw_ball(ctx)
        for cat, sprite in zip(self.cats, self.sprites):
            self._draw_cat(ctx, th, cat, sprite)

    def _draw_floor(self, ctx, th):
        level = self.battery.level
        if self.battery.charging:
            pulse = 0.6 + 0.4 * math.sin(self._t / 300.0)
            base = th["floor_charge"]
            color = (base[0] * pulse, base[1] * pulse, base[2] * pulse)
        elif level is None:
            color = th["floor_ok"]
        else:
            color = theme.battery_color(level, th)
        ctx.save()
        ctx.begin_path()
        ctx.line_width = RING_W
        ctx.rgb(color[0], color[1], color[2])
        ctx.arc(0, 0, RING_R, 0, 2 * math.pi, 0).stroke()
        ctx.restore()

    def _draw_planets(self, ctx):
        # Planets appear behind the yarn and cats — sky, not floor.
        for flash in self.planets.flashes:
            a = flash.alpha()
            if a <= 0.0:
                continue
            size = SIZES[flash.name]
            half = size / 2
            ctx.save()
            ctx.global_alpha = a
            ctx.image_smoothing = 0
            path = self.planet_root + flash.name + ".png"
            ctx.image(path, flash.x - half, flash.y - half, size, size)
            ctx.restore()
            ctx.global_alpha = 1.0  # belt and braces: not all ports restore it

    def _draw_ball(self, ctx):
        half = YARN_SIZE / 2
        ctx.save()
        ctx.translate(self.ball.x, self.ball.y)
        ctx.rotate(self.ball.theta)
        ctx.image_smoothing = 0
        ctx.image(self.yarn_path, -half, -half, YARN_SIZE, YARN_SIZE)
        ctx.restore()

    def _draw_cat(self, ctx, th, cat, sprite):
        ctx.save()
        if cat.state == PERCH:
            # One combined cat-on-ball sprite, feet-outward at the ball's spot.
            ctx.translate(self.ball.x, self.ball.y)
            ctx.rotate(self.ball.phi - HALF_PI)
            sprite.draw(ctx, PERCH_OFF[0], PERCH_OFF[1], PERCH_SIZE)
            ctx.restore()
            return
        ctx.translate(cat.x, cat.y)
        ctx.rotate(cat.phi - HALF_PI)  # feet toward the rim floor
        sx, sy = cat.squash()
        hop = cat.hop_offset()
        sprite.draw(ctx, 0, hop, CAT_SIZE, flip_x=cat.facing_left, sx=sx, sy=sy)
        if cat.show_alert():
            txt = th["text"]
            ctx.rgb(txt[0], txt[1], txt[2])
            top = hop - CAT_SIZE / 2 - 8
            ctx.rectangle(-2, top, 4, 12).fill()
            ctx.rectangle(-2, top + 16, 4, 4).fill()
        ctx.restore()


CatYarnApp.ACTIONS = {"nudge": ["CONFIRM"]}
for _pad in PADS:
    CatYarnApp.ACTIONS[f"planet_{_pad}"] = [f"TOUCH{_pad:02d}"]

__app_export__ = CatYarnApp
