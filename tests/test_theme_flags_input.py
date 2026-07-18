from spmono import flags, theme
from spmono.input.actions import InputMap


def test_theme_defaults_and_selection():
    assert theme.current() == theme.THEMES["spaceagon"]
    theme.select("void")
    assert theme.current() == theme.THEMES["void"]
    theme.select("nonsense")  # ignored
    assert theme.current() == theme.THEMES["void"]
    theme.select("spaceagon")


def test_lerp_clamps():
    a, b = (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)
    assert theme.lerp(a, b, -1) == a
    assert theme.lerp(a, b, 2) == b
    assert theme.lerp(a, b, 0.5) == (0.5, 0.5, 0.5)


def test_flags_roundtrip_and_default():
    assert flags.get("testapp", "missing", 42) == 42
    flags.set("testapp", "toggle", True)
    assert flags.get("testapp", "toggle") is True


def make_map(state):
    m = InputMap({"nudge": ["CONFIRM"], "both": ["UP", "DOWN"]})
    m.attach_provider(lambda key: state.get(key, False))
    return m


def test_exit_binding_always_present():
    m = make_map({})
    assert "exit" in m.bindings and m.bindings["exit"] == ["CANCEL"]


def test_pressed_is_edge_not_level():
    state = {}
    m = make_map(state)
    state["CONFIRM"] = True
    m.update(50)
    assert m.pressed("nudge") and m.held("nudge")
    m.update(50)  # still held (the firmware auto-repeats Down events; we don't)
    assert not m.pressed("nudge") and m.held("nudge")
    state["CONFIRM"] = False
    m.update(50)
    assert m.released("nudge") and not m.held("nudge")


def test_any_bound_key_matches():
    state = {"DOWN": True}
    m = make_map(state)
    m.update(50)
    assert m.held("both")


def test_long_press_fires_once():
    state = {"CONFIRM": True}
    m = make_map(state)
    for _ in range(11):
        m.update(60)  # 660ms held
    assert m.long_pressed("nudge")
    assert not m.long_pressed("nudge")  # once per hold
    state["CONFIRM"] = False
    m.update(50)
    state["CONFIRM"] = True
    m.update(50)
    assert not m.long_pressed("nudge")  # fresh hold, not yet long
