"""Action-map input layer: bind semantic actions to physical inputs.

Bindings target BUTTON_TYPES keys ("UP", "DOWN", "LEFT", "RIGHT", "CONFIRM",
"CANCEL") by default, which covers 2024 buttons, 2026 buttons A-F, AND the
Spaceagon joystick for free (the firmware parents them all onto BUTTON_TYPES).

The firmware auto-repeats ButtonDownEvent every ~200 ms while held, so edge
detection (pressed/released) is done here from held-state transitions, never
from raw Down events. Long-press is layered on top of held time.

Firmware modules are imported lazily inside attach() so pure-logic code and
CPython tests can use InputMap with an injected provider instead.
"""

_LONG_PRESS_MS = 600


class InputMap:
    def __init__(self, bindings=None):
        """bindings: dict action -> list of BUTTON_TYPES key names."""
        self.bindings = dict(bindings or {})
        if "exit" not in self.bindings:
            self.bindings["exit"] = ["CANCEL"]  # every app gets a way out
        self._provider = None  # fn(button_key) -> bool held
        self._buttons = None
        self._held = {}
        self._prev = {}
        self._held_ms = {}
        self._long_fired = {}
        for action in self.bindings:
            self._held[action] = False
            self._prev[action] = False
            self._held_ms[action] = 0
            self._long_fired[action] = False

    def attach(self, app):
        """Wire to the firmware Buttons helper (badge / simulator)."""
        from events.input import BUTTON_TYPES, Buttons

        self._buttons = Buttons(app)

        def provider(key):
            return bool(self._buttons.get(BUTTON_TYPES[key]))

        self._provider = provider

    def attach_provider(self, provider):
        """Inject a fn(button_key) -> bool for tests / custom sources."""
        self._provider = provider

    def clear(self):
        if self._buttons is not None:
            self._buttons.clear()
        for action in self.bindings:
            self._held[action] = False
            self._prev[action] = False
            self._held_ms[action] = 0
            self._long_fired[action] = False

    def update(self, delta_ms):
        if self._provider is None:
            return
        for action, keys in self.bindings.items():
            now = False
            for key in keys:
                if self._provider(key):
                    now = True
                    break
            self._prev[action] = self._held[action]
            self._held[action] = now
            if now:
                self._held_ms[action] += delta_ms
            else:
                self._held_ms[action] = 0
                self._long_fired[action] = False

    def held(self, action):
        return self._held.get(action, False)

    def pressed(self, action):
        return self._held.get(action, False) and not self._prev.get(action, False)

    def released(self, action):
        return self._prev.get(action, False) and not self._held.get(action, False)

    def long_pressed(self, action, ms=_LONG_PRESS_MS):
        """True once per hold, after `ms` of continuous hold."""
        if self._held_ms.get(action, 0) >= ms and not self._long_fired.get(action, False):
            self._long_fired[action] = True
            return True
        return False
