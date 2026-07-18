"""Feature flags backed by the badge settings store (flat shared /settings.json).

Keys are namespaced spmono_<app>_<flag> to coexist with firmware keys (wifi_*,
pattern_*, ...). Falls back to an in-memory dict off-badge so pure-logic tests
need no stubs. Nothing auto-saves on the badge — set() saves explicitly.
"""

_mem = {}


def _key(app, name):
    return "spmono_" + app + "_" + name


def get(app, name, default=None):
    key = _key(app, name)
    try:
        import settings

        return settings.get(key, default)
    except ImportError:
        return _mem.get(key, default)


def set(app, name, value):
    key = _key(app, name)
    try:
        import settings

        settings.set(key, value)
        settings.save()
    except ImportError:
        _mem[key] = value
