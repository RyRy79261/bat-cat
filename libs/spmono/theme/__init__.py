"""Theming engine: semantic color palettes, selected via one settings key.

Shapes mirror the firmware's app_components.tokens ui_colors dict (values are
rgb float tuples 0..1) so themes interoperate with tokens.set_color. Plain
dicts only — MicroPython has no dataclasses.
"""

_SETTINGS_KEY = "spmono_theme"
_mem = {}  # fallback store when the badge settings module is unavailable

THEMES = {
    "spaceagon": {
        "background": (0.0, 0.027, 0.19),  # firmware dark_blue
        "text": (1.0, 1.0, 1.0),
        "floor_ok": (0.16, 0.89, 0.55),  # green
        "floor_mid": (0.97, 0.75, 0.11),  # amber
        "floor_low": (0.92, 0.20, 0.16),  # red
        "floor_charge": (0.18, 0.68, 0.85),  # pale blue pulse
        "accent": (0.97, 0.50, 0.01),  # firmware orange
    },
    "cream": {
        "background": (0.96, 0.93, 0.86),
        "text": (0.15, 0.12, 0.10),
        "floor_ok": (0.30, 0.65, 0.35),
        "floor_mid": (0.85, 0.60, 0.15),
        "floor_low": (0.80, 0.20, 0.15),
        "floor_charge": (0.25, 0.55, 0.80),
        "accent": (0.80, 0.35, 0.25),
    },
    "void": {
        "background": (0.02, 0.02, 0.03),
        "text": (0.85, 0.85, 0.9),
        "floor_ok": (0.0, 0.8, 0.5),
        "floor_mid": (0.9, 0.7, 0.0),
        "floor_low": (0.9, 0.1, 0.2),
        "floor_charge": (0.2, 0.6, 0.9),
        "accent": (0.55, 0.30, 0.85),
    },
}

DEFAULT = "spaceagon"


def _settings_get(key, default):
    try:
        import settings

        return settings.get(key, default)
    except ImportError:
        return _mem.get(key, default)


def _settings_set(key, value):
    try:
        import settings

        settings.set(key, value)
        settings.save()
    except ImportError:
        _mem[key] = value


def current():
    name = _settings_get(_SETTINGS_KEY, DEFAULT)
    return THEMES.get(name, THEMES[DEFAULT])


def select(name):
    if name in THEMES:
        _settings_set(_SETTINGS_KEY, name)


def lerp(a, b, t):
    """Linear-interpolate two rgb tuples; t clamped to 0..1."""
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    return (
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
    )


def battery_color(level, theme=None):
    """Map battery percent (0..100) to floor color: red -> amber -> green."""
    th = theme or current()
    if level >= 60.0:
        return th["floor_ok"]
    if level >= 25.0:
        return lerp(th["floor_mid"], th["floor_ok"], (level - 25.0) / 35.0)
    return lerp(th["floor_low"], th["floor_mid"], level / 25.0)
