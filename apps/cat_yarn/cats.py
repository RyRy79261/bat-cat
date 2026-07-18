"""Cat behavior: pure logic, no firmware imports (unit-testable on CPython).

State machine per cat: IDLE <-> CHASE -> FRIGHT -> CHASE, plus SLEEP after the
ball has been still for a while.

The fright rule (per spec): if the ball changes direction and its new path
would take it past the cat, the cat startles and jumps. Implemented as:
within fright_radius, the ball's velocity flips by more than 90 degrees
(dot(v_new, v_old) < 0) at real speed, and the new trajectory's closest
approach to the cat is under pass_dist.
"""

import math

IDLE = 0
CHASE = 1
FRIGHT = 2
SLEEP = 3

HOP_MS = 450
HOP_HEIGHT = 10.0
FRIGHT_COOLDOWN_MS = 800
SLEEP_AFTER_MS = 20000
BALL_STILL_SPEED = 5.0
BALL_WAKE_SPEED = 15.0
MIN_FLIP_SPEED = 25.0


class Cat:
    def __init__(
        self,
        x,
        y,
        speed=60.0,
        accel=150.0,
        standoff=20.0,
        fright_radius=48.0,
        pass_dist=28.0,
        play_radius=95.0,
    ):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.max_speed = speed
        self.accel = accel
        self.standoff = standoff
        self.fright_radius = fright_radius
        self.pass_dist = pass_dist
        self.play_radius = play_radius
        self.state = IDLE
        self.state_ms = 0
        self.facing_left = False
        self._prev_bvx = 0.0
        self._prev_bvy = 0.0
        self._cooldown_ms = 0
        self._still_ms = 0

    # -- queries used by the renderer ------------------------------------

    def hop_offset(self):
        """Vertical fright-hop offset in px (negative = up)."""
        if self.state != FRIGHT:
            return 0.0
        t = self.state_ms / HOP_MS
        if t > 1.0:
            t = 1.0
        return -HOP_HEIGHT * math.sin(math.pi * t)

    def squash(self):
        """(sx, sy) landing squash during the last part of the hop."""
        if self.state == FRIGHT and self.state_ms > HOP_MS - 100:
            return (1.1, 0.9)
        return (1.0, 1.0)

    def anim(self):
        if self.state == SLEEP:
            return "sleep"
        if self.state == FRIGHT:
            return "fright_up" if self.state_ms < HOP_MS / 2 else "fright_down"
        if self.state == CHASE:
            return "run"
        return "idle"

    def show_alert(self):
        return self.state == FRIGHT and self.state_ms < 250

    # -- update ----------------------------------------------------------

    def update(self, delta_ms, ball):
        dt = delta_ms / 1000.0
        self.state_ms += delta_ms
        if self._cooldown_ms > 0:
            self._cooldown_ms -= delta_ms

        bspeed = math.sqrt(ball.vx * ball.vx + ball.vy * ball.vy)
        if bspeed < BALL_STILL_SPEED:
            self._still_ms += delta_ms
        else:
            self._still_ms = 0

        if self.state == FRIGHT:
            if self.state_ms >= HOP_MS:
                self._set(CHASE)
                self._cooldown_ms = FRIGHT_COOLDOWN_MS
        elif self._fright_triggered(ball, bspeed):
            self._set(FRIGHT)
            self.vx = 0.0
            self.vy = 0.0
        elif self.state == SLEEP:
            if bspeed > BALL_WAKE_SPEED:
                self._set(IDLE)
        else:
            dx = ball.x - self.x
            dy = ball.y - self.y
            dist = math.sqrt(dx * dx + dy * dy)
            if self._still_ms > SLEEP_AFTER_MS:
                self._set(SLEEP)
                self.vx = 0.0
                self.vy = 0.0
            elif dist > self.standoff + 6.0:
                self._set(CHASE)
                self._seek(dx, dy, dist, dt)
            else:
                self._set(IDLE)
                self.vx *= 0.7
                self.vy *= 0.7

        if self.state == CHASE or self.state == IDLE:
            self.x += self.vx * dt
            self.y += self.vy * dt
            d = math.sqrt(self.x * self.x + self.y * self.y)
            if d > self.play_radius and d > 0.0:
                self.x *= self.play_radius / d
                self.y *= self.play_radius / d
            if abs(self.vx) > 2.0:
                self.facing_left = self.vx < 0.0

        self._prev_bvx = ball.vx
        self._prev_bvy = ball.vy

    def _set(self, state):
        if state != self.state:
            self.state = state
            self.state_ms = 0

    def _seek(self, dx, dy, dist, dt):
        if dist <= 0.0:
            return
        ux = dx / dist
        uy = dy / dist
        self.vx += ux * self.accel * dt
        self.vy += uy * self.accel * dt
        spd = math.sqrt(self.vx * self.vx + self.vy * self.vy)
        if spd > self.max_speed:
            k = self.max_speed / spd
            self.vx *= k
            self.vy *= k

    def _fright_triggered(self, ball, bspeed):
        if self.state == FRIGHT or self._cooldown_ms > 0:
            return False
        prev_speed = math.sqrt(self._prev_bvx * self._prev_bvx + self._prev_bvy * self._prev_bvy)
        if bspeed < MIN_FLIP_SPEED or prev_speed < MIN_FLIP_SPEED:
            return False
        # Direction flip of more than 90 degrees?
        if ball.vx * self._prev_bvx + ball.vy * self._prev_bvy >= 0.0:
            return False
        rx = self.x - ball.x
        ry = self.y - ball.y
        dist = math.sqrt(rx * rx + ry * ry)
        if dist > self.fright_radius:
            return False
        # Closest approach of the new trajectory to the cat.
        ux = ball.vx / bspeed
        uy = ball.vy / bspeed
        t = rx * ux + ry * uy
        if t <= 0.0:
            return False  # heading away — it won't pass us
        cx = rx - t * ux
        cy = ry - t * uy
        return math.sqrt(cx * cx + cy * cy) < self.pass_dist
