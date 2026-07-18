from cat_yarn_cats import CHASE, FRIGHT, HOP_MS, IDLE, SLEEP, Cat


class Ball:
    def __init__(self, x=0.0, y=0.0, vx=0.0, vy=0.0):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy


def settle(cat, ball, steps=1, delta=50):
    for _ in range(steps):
        cat.update(delta, ball)


def test_cat_chases_distant_ball():
    cat = Cat(0.0, 0.0)
    ball = Ball(x=80.0, y=0.0, vx=0.0, vy=0.0)
    settle(cat, ball, steps=10)
    assert cat.state == CHASE
    assert cat.x > 0  # moved toward the ball
    assert not cat.facing_left


def test_cat_idles_next_to_still_ball():
    cat = Cat(10.0, 0.0)
    ball = Ball(x=12.0, y=0.0)
    settle(cat, ball, steps=5)
    assert cat.state == IDLE


def test_fright_on_reversal_that_passes_cat():
    cat = Cat(30.0, 0.0)
    ball = Ball(x=0.0, y=0.0, vx=60.0, vy=0.0)  # approaching the cat
    settle(cat, ball, steps=2)
    assert cat.state != FRIGHT
    ball.vx = -60.0  # full reversal within fright radius, path passes the cat? no —
    # reversal heads AWAY from the cat -> t <= 0 -> no fright
    settle(cat, ball)
    assert cat.state != FRIGHT

    # Now the mirrored case: ball moving away flips back toward + past the cat.
    cat = Cat(30.0, 0.0, standoff=5.0)
    ball = Ball(x=60.0, y=2.0, vx=55.0, vy=0.0)  # moving away from cat
    settle(cat, ball, steps=2)
    ball.vx = -55.0  # reverses: new path passes right by the cat
    settle(cat, ball)
    assert cat.state == FRIGHT


def test_no_fright_when_far_away():
    cat = Cat(0.0, -90.0)
    ball = Ball(x=0.0, y=90.0, vx=50.0, vy=0.0)
    settle(cat, ball, steps=2)
    ball.vx = -50.0
    settle(cat, ball)
    assert cat.state != FRIGHT


def test_fright_ends_and_cooldown_blocks_retrigger():
    cat = Cat(30.0, 0.0)
    ball = Ball(x=60.0, y=2.0, vx=55.0, vy=0.0)
    settle(cat, ball, steps=2)
    ball.vx = -55.0
    settle(cat, ball)
    assert cat.state == FRIGHT
    settle(cat, ball, steps=HOP_MS // 50 + 2)
    assert cat.state != FRIGHT
    # Immediate second reversal during cooldown must not re-trigger.
    ball.vx = 55.0
    settle(cat, ball)
    ball.vx = -55.0
    settle(cat, ball)
    assert cat.state != FRIGHT


def test_hop_offset_peaks_mid_jump():
    cat = Cat(30.0, 0.0)
    ball = Ball(x=60.0, y=2.0, vx=55.0, vy=0.0)
    settle(cat, ball, steps=2)
    ball.vx = -55.0
    settle(cat, ball)
    assert cat.state == FRIGHT
    settle(cat, ball, steps=4)  # ~mid-hop
    assert cat.hop_offset() < -5.0  # up = negative y


def test_sleep_after_still_ball_and_wake_on_motion():
    cat = Cat(10.0, 0.0)
    ball = Ball(x=12.0, y=0.0)
    settle(cat, ball, steps=450)  # > 20s of stillness at 50ms ticks
    assert cat.state == SLEEP
    ball.vx = 40.0
    settle(cat, ball)
    assert cat.state != SLEEP
