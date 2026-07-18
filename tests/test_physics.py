import math

import pytest
from spmono.engine.physics import RimBall, TiltBall


def make_ball():
    return TiltBall(radius=12, play_radius=99, deadzone=0.8)


def test_tilt_accelerates_ball():
    ball = make_ball()
    for _ in range(20):
        ball.step(3.0, 0.0, 0.05)
    assert ball.vx > 0
    assert ball.x > 0
    assert ball.vy == 0


def test_deadzone_ignores_small_tilt():
    ball = make_ball()
    for _ in range(20):
        ball.step(0.5, 0.5, 0.05)  # below 0.8 m/s^2 magnitude combined? no —
    # magnitude ~0.707 < 0.8 -> ignored entirely
    assert ball.vx == 0
    assert ball.vy == 0


def test_friction_decays_velocity():
    ball = make_ball()
    ball.vx = 100.0
    for _ in range(40):
        ball.step(0.0, 0.0, 0.05)
    assert abs(ball.vx) < 15.0


def test_ball_stays_inside_play_circle():
    ball = make_ball()
    for _ in range(400):
        ball.step(9.8, 0.0, 0.05)
        assert math.hypot(ball.x, ball.y) <= ball.play_radius + 1e-6


def test_bounce_reverses_normal_velocity():
    ball = make_ball()
    ball.x = 98.9
    ball.vx = 120.0
    ball.step(0.0, 0.0, 0.05)
    assert ball.vx < 0  # reflected
    assert abs(ball.vx) < 120.0  # damped


def test_roll_angle_advances_with_motion():
    ball = make_ball()
    for _ in range(10):
        ball.step(5.0, 0.0, 0.05)
    assert ball.theta != 0.0


# -- RimBall: the rim-floor track --------------------------------------------


def make_rim_ball():
    return RimBall(radius=13, track_radius=98.5)


def test_rim_ball_stays_on_track():
    ball = make_rim_ball()
    for _ in range(200):
        ball.step(9.8, 3.0, 0.05)
        assert math.hypot(ball.x, ball.y) == pytest.approx(ball.track_r)


def test_rim_ball_slides_toward_gravity_low_point():
    ball = make_rim_ball()  # starts at the bottom (phi = pi/2)
    # Gravity to screen-right: the low point is phi = 0.
    for _ in range(400):
        ball.step(9.8, 0.0, 0.05)
    assert abs(math.sin(ball.phi)) < 0.5  # settled near the right side
    assert ball.x > 0


def test_rim_ball_deadzone_keeps_it_still():
    ball = make_rim_ball()
    for _ in range(20):
        ball.step(0.5, 0.5, 0.05)  # magnitude ~0.7 < 0.8 deadzone
    assert ball.v == 0.0
    assert ball.phi == math.pi / 2


def test_rim_ball_rolls_as_it_moves():
    ball = make_rim_ball()
    for _ in range(10):
        ball.step(9.8, 0.0, 0.05)
    assert ball.theta != 0.0
