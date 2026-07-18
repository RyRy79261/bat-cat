"""BaseApp: App subclass wiring the input layer, theme access, the guaranteed
CANCEL -> minimise exit, and an optional fps/mem debug overlay.

Subclasses implement on_update(delta) / on_draw(ctx) and may set ACTIONS to
extend input bindings ("exit" -> CANCEL is always present).
"""

# Import order matters: firmware's app -> system.eventbus -> system.scheduler
# is circular unless system.scheduler loads first. On the badge it already has;
# in the simulator's app-override mode (run.py <module>.<Class>) it has NOT,
# and importing `app` first crashes (upstream bug, present in OS v2.1.1 —
# even sim/apps/example fails). Priming scheduler makes the cycle resolve.
import system.scheduler  # noqa: F401  (must precede `from app import App`)
from app import App

from .. import theme as _theme
from ..input.actions import InputMap


class BaseApp(App):
    ACTIONS = {}

    def __init__(self):
        super().__init__()
        self.inputs = InputMap(dict(self.ACTIONS))
        self.inputs.attach(self)
        self.debug = False

    @property
    def theme(self):
        return _theme.current()

    def update(self, delta):
        self.inputs.update(delta)
        if self.inputs.pressed("exit"):
            self.on_minimise()
            self.inputs.clear()  # else the app reopens itself on refocus
            self.minimise()
            return False
        return self.on_update(delta)

    def draw(self, ctx):
        self.on_draw(ctx)
        if self.debug:
            self._draw_debug(ctx)
        self.draw_overlays(ctx)

    def on_update(self, delta):
        return False

    def on_draw(self, ctx):
        pass

    def on_minimise(self):
        """Hook: restore shared state (LED patterns etc.) before minimising."""
        pass

    def _draw_debug(self, ctx):
        try:
            import gc

            import display

            line = f"{display.get_fps():.0f}fps {gc.mem_free() // 1024}k"
        except (ImportError, AttributeError):
            line = "debug"
        ctx.save()
        ctx.rgb(1.0, 1.0, 1.0)
        ctx.font_size = 12
        ctx.text_align = ctx.CENTER
        ctx.move_to(0, 100)
        ctx.text(line)
        ctx.restore()
