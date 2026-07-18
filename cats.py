"""Cat behavior: pure logic, no firmware imports (unit-testable on CPython).

The screen's rim is the floor. Cats, like the ball, live ON the rim: each cat
is a bead on a circular track at angle phi, sliding under the tangential
component of tilt gravity and running along the track after the ball. Nothing
ever leaves the floor, and sprites are drawn feet-outward at their track
angle, so a cat can never end up on its head.

State machine per cat:

    IDLE <-> CHASE -> JUMP   (ball rolls at the cat -> it leaps over the ball)
                   -> FRIGHT (ball reverses past the cat -> startle hop)
    IDLE/CHASE     -> PERCH  (cat reaches a still ball -> sits, then lies, on it)
    IDLE           -> SLEEP  (ball still for a while)

Cats share the ball's tilt physics — the same gravity scale, friction, and
speed cap as spmono.engine.physics.RimBall — so they fall exactly like the
ball does. Their self-powered chase (run acceleration) is deliberately weaker,
so a cat runs slower than the ball rolls.
"""

import math

IDLE = 0
CHASE = 1
FRIGHT = 2
SLEEP = 3
JUMP = 4
PERCH = 5

TWO_PI = 2.0 * math.pi

HOP_MS = 450
HOP_HEIGHT = 20.0
JUMP_MS = 520
JUMP_HEIGHT = 40.0
FRIGHT_COOLDOWN_MS = 800
SLEEP_AFTER_MS = 20000
BALL_STILL_SPEED = 5.0
BALL_WAKE_SPEED = 15.0
MIN_FLIP_SPEED = 25.0
JUMP_MIN_SPEED = 45.0
PERCH_ON_DIST = 12.0
PERCH_OFF_SPEED = 40.0
PERCH_LIE_AFTER_MS = 6000
MIN_SEPARATION = 52.0  # arc px between cat centres — cats never stack

# Tilt physics — MUST match spmono.engine.physics.RimBall's defaults so the
# cats fall under the same gravity as the ball. (Duplicated, not imported:
# this module stays import-free so it unit-tests standalone on CPython.)
GRAV_SCALE = 40.0
GRAV_DEADZONE = 0.8
FRICTION = 1.1
MAX_SPEED = 340.0


def arc_delta(from_phi, to_phi):
    """Shortest signed angular difference to get from from_phi to to_phi."""
    return (to_phi - from_phi + math.pi) % TWO_PI - math.pi


def separate(cats):
    """Keep cats at least MIN_SEPARATION arc px apart so none hides behind
    another. Call once per tick after every cat has updated. Airborne or
    perched cats hold their spot; grounded ones get nudged."""
    for i in range(len(cats)):
        for j in range(i + 1, len(cats)):
            a, b = cats[i], cats[j]
            gap = arc_delta(a.phi, b.phi) * a.track_r  # signed arc a -> b
            overlap = MIN_SEPARATION - abs(gap)
            if overlap <= 0.0:
                continue
            sign = 1.0 if gap >= 0.0 else -1.0  # push b to +sign, a to -sign
            a_free = a.state in (IDLE, CHASE, SLEEP)
            b_free = b.state in (IDLE, CHASE, SLEEP)
            if a_free and b_free:
                a.phi -= sign * (overlap / 2) / a.track_r
                b.phi += sign * (overlap / 2) / b.track_r
            elif a_free:
                a.phi -= sign * overlap / a.track_r
            elif b_free:
                b.phi += sign * overlap / b.track_r
            a.phi %= TWO_PI
            b.phi %= TWO_PI


class Cat:
    def __init__(
        self,
        phi,
        track_radius=95.0,
        accel=120.0,
        standoff=56.0,
        fright_dist=90.0,
    ):
        self.phi = phi % TWO_PI
        self.track_r = track_radius
        self.v = 0.0  # linear speed along the track, px/s (positive = +phi)
        self.accel = accel
        self.standoff = standoff
        self.fright_dist = fright_dist
        self.state = IDLE
        self.state_ms = 0
        self.facing_left = False
        self._prev_bv = 0.0
        self._cooldown_ms = 0
        self._still_ms = 0

    # -- queries used by the renderer ------------------------------------

    @property
    def x(self):
        return self.track_r * math.cos(self.phi)

    @property
    def y(self):
        return self.track_r * math.sin(self.phi)

    def hop_offset(self):
        """Hop offset in px along the local up (negative = off the floor)."""
        if self.state == FRIGHT:
            span, height = HOP_MS, HOP_HEIGHT
        elif self.state == JUMP:
            span, height = JUMP_MS, JUMP_HEIGHT
        else:
            return 0.0
        t = self.state_ms / span
        if t > 1.0:
            t = 1.0
        return -height * math.sin(math.pi * t)

    def squash(self):
        """(sx, sy) landing squash during the last part of the fright hop."""
        if self.state == FRIGHT and self.state_ms > HOP_MS - 100:
            return (1.1, 0.9)
        return (1.0, 1.0)

    def anim(self):
        if self.state == SLEEP:
            return "sleep"
        if self.state == PERCH:
            return "perch_sit" if self.state_ms < PERCH_LIE_AFTER_MS else "perch_lie"
        if self.state == JUMP:
            return "jump_up" if self.state_ms < JUMP_MS / 2 else "jump_down"
        if self.state == FRIGHT:
            return "fright_up" if self.state_ms < HOP_MS / 2 else "fright_down"
        if self.state == CHASE:
            return "run"
        return "idle"

    def show_alert(self):
        return self.state == FRIGHT and self.state_ms < 250

    # -- update ----------------------------------------------------------

    def update(self, delta_ms, ball, gx=0.0, gy=0.0, can_perch=False):
        """Advance the cat.

        ball: exposes phi (track angle) and v (linear track speed, px/s) —
        RimBall, or any stub with those two attributes.
        gx, gy: screen-space tilt acceleration (m/s^2) — the same values the
        app feeds RimBall.step, so cat and ball share one gravity.
        can_perch: whether this cat may (or already does) sit on the ball —
        the app grants it to one cat at a time.
        """
        dt = delta_ms / 1000.0
        self.state_ms += delta_ms
        if self._cooldown_ms > 0:
            self._cooldown_ms -= delta_ms

        bspeed = abs(ball.v)
        if bspeed < BALL_STILL_SPEED:
            self._still_ms += delta_ms
        else:
            self._still_ms = 0

        # Signed arc from cat to ball, in px along the track.
        gap = arc_delta(self.phi, ball.phi) * self.track_r
        dist = abs(gap)

        if self.state == PERCH:
            self.phi = ball.phi
            if bspeed > PERCH_OFF_SPEED or not can_perch:
                self._set(FRIGHT)  # knocked off — startle hop
                self.v = 0.0
                self._cooldown_ms = FRIGHT_COOLDOWN_MS
        elif self.state == FRIGHT or self.state == JUMP:
            span = HOP_MS if self.state == FRIGHT else JUMP_MS
            if self.state_ms >= span:
                self._set(CHASE)
                self._cooldown_ms = FRIGHT_COOLDOWN_MS
        elif self._fright_triggered(ball, bspeed, gap):
            self._set(FRIGHT)
            self.v = 0.0
        elif self._jump_triggered(ball, bspeed, gap):
            self._set(JUMP)
            self.v = 0.0
        elif self.state == SLEEP:
            if bspeed > BALL_WAKE_SPEED:
                self._set(IDLE)
        elif can_perch and bspeed < BALL_STILL_SPEED and dist < PERCH_ON_DIST:
            self._set(PERCH)
            self.v = 0.0
        elif self._still_ms > SLEEP_AFTER_MS and dist <= self.standoff + 6.0:
            self._set(SLEEP)
        elif dist > self.standoff + 6.0 or (can_perch and bspeed < BALL_STILL_SPEED):
            # Chase — all the way onto the ball when a perch is on offer.
            self._set(CHASE)
            self.v += (self.accel if gap > 0.0 else -self.accel) * dt
        else:
            self._set(IDLE)

        if self.state in (IDLE, CHASE, SLEEP):
            self._step_physics(gx, gy, dt)
            # Sprite-local right on screen is the -phi track direction, so a
            # cat moving with v > 0 shows its left side.
            if abs(self.v) > 2.0:
                self.facing_left = self.v > 0.0

        self._prev_bv = ball.v

    def _set(self, state):
        if state != self.state:
            self.state = state
            self.state_ms = 0

    def _step_physics(self, gx, gy, dt):
        """Tilt gravity + friction along the rim — the ball's physics, shared."""
        if math.sqrt(gx * gx + gy * gy) < GRAV_DEADZONE:
            a_t = 0.0
        else:
            a_t = gx * -math.sin(self.phi) + gy * math.cos(self.phi)
        self.v += a_t * GRAV_SCALE * dt

        decay = 1.0 - FRICTION * dt
        if self.state != CHASE:
            decay -= 3.0 * dt  # no legs pushing — settle sooner
        if decay < 0.0:
            decay = 0.0
        self.v *= decay

        if self.v > MAX_SPEED:
            self.v = MAX_SPEED
        elif self.v < -MAX_SPEED:
            self.v = -MAX_SPEED

        self.phi = (self.phi + self.v / self.track_r * dt) % TWO_PI

    def _fright_triggered(self, ball, bspeed, gap):
        """Ball reversed direction and its new path passes the cat."""
        if self._cooldown_ms > 0:
            return False
        if bspeed < MIN_FLIP_SPEED or abs(self._prev_bv) < MIN_FLIP_SPEED:
            return False
        if ball.v * self._prev_bv >= 0.0:
            return False  # no reversal
        if abs(gap) > self.fright_dist:
            return False
        # Heading toward the cat? (gap is measured cat->ball, so the ball
        # closes it by moving against the gap's sign.)
        return ball.v * gap < 0.0

    def _jump_triggered(self, ball, bspeed, gap):
        """Ball simply rolling at the cat fast enough to pass it."""
        if self._cooldown_ms > 0 or bspeed < JUMP_MIN_SPEED:
            return False
        return abs(gap) <= self.fright_dist and ball.v * gap < 0.0
