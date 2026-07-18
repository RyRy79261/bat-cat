"""bat-cat — ambient toy for the EMF Spaceagon/Tildagon badge.

A ball of yarn rolls with real gravity (accelerometer); cats chase it and
startle-jump when it reverses past them. The screen's rim is the floor: a thin
ring color-coded by battery level. Leave it running; put the app's menu name in
/autoexec.bat to boot straight into it.
"""

import math


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

from .cats import Cat
from .spmono import flags, theme
from .spmono.engine.physics import TiltBall
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

SCREEN_R = 120
RING_R = 114
RING_W = 5
BALL_R = 12  # 24 px diameter = 10% of screen height
CAT_SIZE = 24  # sprite canvas; cat art is 19 px tall incl. tail (8%)
PLAY_R = RING_R - RING_W / 2 - BALL_R  # ball-centre boundary
CAT_PLAY_R = RING_R - RING_W / 2 - CAT_SIZE / 2

IDLE_REDRAW_MS = 500

_FRAMES = {
    "idle": [("cat/default/idle0.png", 500), ("cat/default/idle1.png", 500)],
    "run": [
        ("cat/default/run0.png", 130),
        ("cat/default/run1.png", 130),
        ("cat/default/run2.png", 130),
    ],
    "fright_up": [("cat/default/fright0.png", 1000)],
    "fright_down": [("cat/default/fright1.png", 1000)],
    "sleep": [("cat/default/sleep0.png", 1000)],
}


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
        self.ball = TiltBall(BALL_R, PLAY_R)
        self.ball.x = 30.0
        self.battery = BatteryMonitor()

        n = flags.get(APP, "max_cats", 2)
        n = 1 if n < 1 else (3 if n > 3 else n)
        anims = _abs_frames(_APP_ROOT)
        self.cats = []
        self.sprites = []
        for i in range(n):
            angle = 2.4 + i * 2.1
            cat = Cat(60.0 * math.cos(angle), 60.0 * math.sin(angle), play_radius=CAT_PLAY_R)
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
            self.ball.vx += 90.0 * math.cos(self.ball.theta)
            self.ball.vy += 90.0 * math.sin(self.ball.theta)

        active = self.ball.speed() > 2.0
        for cat, sprite in zip(self.cats, self.sprites):
            cat.update(delta, self.ball)
            sprite.set_anim(cat.anim())
            sprite.update(delta)
            if cat.state in (1, 2):  # CHASE or FRIGHT
                active = True

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
            for sprite in self.sprites[:1]:
                for path in sprite.all_paths():
                    ctx.image_smoothing = 0
                    ctx.image(path, -12, -12, CAT_SIZE, CAT_SIZE)
            self._prewarmed = True

        bg = th["background"]
        ctx.rgb(bg[0], bg[1], bg[2]).rectangle(-120, -120, 240, 240).fill()

        self._draw_floor(ctx, th)
        self._draw_ball(ctx, th)
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

    def _draw_ball(self, ctx, th):
        acc_color = th["accent"]
        dark = (acc_color[0] * 0.55, acc_color[1] * 0.55, acc_color[2] * 0.55)
        ctx.save()
        ctx.translate(self.ball.x, self.ball.y)
        ctx.rotate(self.ball.theta)
        ctx.begin_path()
        ctx.rgb(acc_color[0], acc_color[1], acc_color[2])
        ctx.arc(0, 0, BALL_R, 0, 2 * math.pi, 0).fill()
        # Yarn strands: three chords that visibly roll with the ball.
        ctx.rgb(dark[0], dark[1], dark[2])
        ctx.line_width = 1.5
        for i in range(3):
            a = i * math.pi / 3.0
            ctx.begin_path()
            ctx.arc(0, 0, BALL_R - 2.5, a, a + math.pi * 0.8, 0).stroke()
        # Loose end trailing out of the ball.
        ctx.begin_path()
        ctx.move_to(BALL_R - 2, 2)
        ctx.line_to(BALL_R + 5, 5)
        ctx.stroke()
        ctx.restore()

    def _draw_cat(self, ctx, th, cat, sprite):
        sx, sy = cat.squash()
        sprite.draw(
            ctx,
            cat.x,
            cat.y + cat.hop_offset(),
            CAT_SIZE,
            flip_x=cat.facing_left,
            sx=sx,
            sy=sy,
        )
        if cat.show_alert():
            txt = th["text"]
            ctx.save()
            ctx.rgb(txt[0], txt[1], txt[2])
            top = cat.y + cat.hop_offset() - CAT_SIZE
            ctx.rectangle(cat.x - 1, top, 2, 6).fill()
            ctx.rectangle(cat.x - 1, top + 8, 2, 2).fill()
            ctx.restore()


CatYarnApp.ACTIONS = {"nudge": ["CONFIRM"]}

__app_export__ = CatYarnApp
