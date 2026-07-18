from spmono.engine.sprite import Sprite

ANIMS = {
    "idle": [("idle0.png", 500), ("idle1.png", 500)],
    "run": [("run0.png", 100), ("run1.png", 100), ("run2.png", 100)],
    "sleep": [("sleep0.png", 1000)],
}


def test_frames_advance_on_schedule():
    s = Sprite(ANIMS, "run")
    assert s.path() == "run0.png"
    s.update(99)
    assert s.path() == "run0.png"
    s.update(1)
    assert s.path() == "run1.png"
    s.update(250)
    assert s.path() == "run0.png"  # wrapped past run2


def test_set_anim_resets_only_on_change():
    s = Sprite(ANIMS, "run")
    s.update(150)
    assert s.index == 1
    s.set_anim("run")
    assert s.index == 1  # unchanged
    s.set_anim("idle")
    assert s.index == 0 and s.path() == "idle0.png"


def test_single_frame_anim_never_advances():
    s = Sprite(ANIMS, "sleep")
    s.update(10_000)
    assert s.path() == "sleep0.png"


def test_all_paths_unique():
    s = Sprite(ANIMS, "idle")
    paths = s.all_paths()
    assert len(paths) == len(set(paths)) == 6
