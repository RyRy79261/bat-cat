"""Tilt-driven ball physics constrained to the round screen.

Screen space: origin at display centre, +x right, +y down (ctx convention).
Callers map accelerometer axes to screen space before calling step():
on the badge that is ax_screen = acc[1], ay_screen = acc[0] (no sign flips).
"""

import math


class TiltBall:
    def __init__(
        self,
        radius,
        play_radius,
        accel_scale=40.0,
        friction=1.1,
        restitution=0.55,
        deadzone=0.8,
        max_speed=340.0,
    ):
        self.r = radius
        self.play_radius = play_radius
        self.accel_scale = accel_scale
        self.friction = friction
        self.restitution = restitution
        self.deadzone = deadzone
        self.max_speed = max_speed
        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.theta = 0.0  # visual roll angle, radians

    def speed(self):
        return math.sqrt(self.vx * self.vx + self.vy * self.vy)

    def step(self, ax, ay, dt):
        """Advance by dt seconds under screen-space tilt acceleration (m/s^2)."""
        mag = math.sqrt(ax * ax + ay * ay)
        if mag < self.deadzone:
            ax = 0.0
            ay = 0.0
        self.vx += ax * self.accel_scale * dt
        self.vy += ay * self.accel_scale * dt

        decay = 1.0 - self.friction * dt
        if decay < 0.0:
            decay = 0.0
        self.vx *= decay
        self.vy *= decay

        spd = self.speed()
        if spd > self.max_speed:
            k = self.max_speed / spd
            self.vx *= k
            self.vy *= k
            spd = self.max_speed

        self.x += self.vx * dt
        self.y += self.vy * dt

        # Circular boundary: reflect along the outward normal, damped.
        dist = math.sqrt(self.x * self.x + self.y * self.y)
        if dist > self.play_radius and dist > 0.0:
            nx = self.x / dist
            ny = self.y / dist
            self.x = nx * self.play_radius
            self.y = ny * self.play_radius
            vn = self.vx * nx + self.vy * ny
            if vn > 0.0:
                self.vx -= (1.0 + self.restitution) * vn * nx
                self.vy -= (1.0 + self.restitution) * vn * ny

        # Visual roll: spin proportional to travel, signed by dominant motion.
        if spd > 1.0:
            sign = 1.0 if (self.vx if abs(self.vx) >= abs(self.vy) else self.vy) >= 0 else -1.0
            self.theta += sign * (spd / self.r) * dt
