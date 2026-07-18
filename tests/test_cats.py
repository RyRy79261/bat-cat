import math

from cat_yarn_cats import (
    CHASE,
    FRIGHT,
    HOP_MS,
    IDLE,
    JUMP,
    JUMP_MS,
    PERCH,
    PERCH_LIE_AFTER_MS,
    SLEEP,
    Cat,
)

R = 95.0  # track radius used throughout — arc px = angle * R


class Ball:
    """RimBall stand-in: just a track angle and a linear track speed."""

    def __init__(self, phi=math.pi / 2, v=0.0):
        self.phi = phi
        self.v = v


def arc(px):
    return px / R


def settle(cat, ball, steps=1, delta=50, **kw):
    for _ in range(steps):
        cat.update(delta, ball, **kw)


def make_cat(gap_px, **kw):
    """Cat sitting gap_px along the track from a ball at the bottom."""
    return Cat(math.pi / 2 - arc(gap_px), track_radius=R, **kw)


def test_cat_chases_distant_ball():
    cat = make_cat(80.0)
    ball = Ball()
    settle(cat, ball, steps=10)
    assert cat.state == CHASE
    # Gap closes: the cat ran toward the ball.
    assert abs(ball.phi - cat.phi) * R < 80.0
    assert cat.facing_left  # moving in +phi shows the sprite's left side


def test_cat_idles_next_to_still_ball():
    cat = make_cat(2.0)
    ball = Ball()
    settle(cat, ball, steps=5)
    assert cat.state == IDLE


def test_jump_when_ball_rolls_at_cat():
    cat = make_cat(30.0)
    ball = Ball(v=-60.0)  # rolling toward the cat (closing a negative gap)
    settle(cat, ball)
    assert cat.state == JUMP
    settle(cat, ball, steps=5)  # ~mid-leap
    assert cat.hop_offset() < -8.0  # well off the floor
    settle(cat, ball, steps=JUMP_MS // 50 + 2)
    assert cat.state != JUMP


def test_no_jump_when_ball_rolls_away():
    cat = make_cat(30.0)
    ball = Ball(v=60.0)  # rolling away from the cat
    settle(cat, ball, steps=3)
    assert cat.state not in (JUMP, FRIGHT)


def test_fright_on_reversal_toward_cat():
    cat = make_cat(30.0)
    ball = Ball(v=55.0)  # moving away
    settle(cat, ball, steps=2)
    assert cat.state not in (JUMP, FRIGHT)
    ball.v = -55.0  # reverses: now heading back past the cat
    settle(cat, ball)
    assert cat.state == FRIGHT  # a flip startles — it beats a plain jump


def test_no_fright_when_far_away():
    cat = make_cat(180.0)
    ball = Ball(v=55.0)
    settle(cat, ball, steps=2)
    ball.v = -55.0
    settle(cat, ball)
    assert cat.state not in (JUMP, FRIGHT)


def test_fright_ends_and_cooldown_blocks_retrigger():
    cat = make_cat(30.0)
    ball = Ball(v=55.0)
    settle(cat, ball, steps=2)
    ball.v = -55.0
    settle(cat, ball)
    assert cat.state == FRIGHT
    settle(cat, ball, steps=HOP_MS // 50 + 2)
    assert cat.state != FRIGHT
    # Immediate second reversal during cooldown must not re-trigger.
    ball.v = 55.0
    settle(cat, ball)
    ball.v = -55.0
    settle(cat, ball)
    assert cat.state != FRIGHT


def test_sleep_after_still_ball_and_wake_on_motion():
    cat = make_cat(2.0)
    ball = Ball()
    settle(cat, ball, steps=450)  # > 20s of stillness at 50ms ticks
    assert cat.state == SLEEP
    ball.v = 40.0
    settle(cat, ball)
    assert cat.state != SLEEP


def test_gravity_slides_cat_like_the_ball():
    cat = make_cat(0.0)
    cat.phi = math.pi / 2  # bottom of the screen
    ball = Ball(phi=math.pi / 2 + arc(150.0))  # far away, so no idle standoff
    # Gravity to screen-right: the low point is phi = 0, behind the cat's
    # chase direction — but strong tilt must win over its legs.
    settle(cat, ball, steps=100, gx=9.8, gy=0.0)
    assert math.cos(cat.phi) > 0.5  # slid toward the gravity-low point


def test_perch_on_still_ball_then_lie_down():
    cat = make_cat(30.0)
    ball = Ball()
    settle(cat, ball, steps=60, can_perch=True)
    assert cat.state == PERCH
    assert cat.phi == ball.phi  # riding the ball
    assert cat.anim() == "perch_sit"
    settle(cat, ball, steps=PERCH_LIE_AFTER_MS // 50 + 2, can_perch=True)
    assert cat.anim() == "perch_lie"


def test_no_perch_without_permission():
    cat = make_cat(30.0)
    ball = Ball()
    settle(cat, ball, steps=60, can_perch=False)
    assert cat.state != PERCH


def test_knocked_off_perch_when_ball_rolls():
    cat = make_cat(30.0)
    ball = Ball()
    settle(cat, ball, steps=60, can_perch=True)
    assert cat.state == PERCH
    ball.v = 80.0  # yanked into motion under the cat
    settle(cat, ball, can_perch=True)
    assert cat.state == FRIGHT
