"""Frame-set sprite animation player. Frames are (image_path, duration_ms) tuples.

ctx decodes each PNG once into a persistent path-keyed texture cache (32 slots),
so drawing the same paths every frame is cheap. Keep total distinct paths low.
"""


class Sprite:
    def __init__(self, anims, initial):
        """anims: dict name -> list of (path, duration_ms)."""
        self.anims = anims
        self.name = initial
        self.index = 0
        self.elapsed = 0

    def set_anim(self, name, restart=False):
        if name == self.name and not restart:
            return
        self.name = name
        self.index = 0
        self.elapsed = 0

    def update(self, delta_ms):
        frames = self.anims[self.name]
        if len(frames) == 1:
            return
        self.elapsed += delta_ms
        dur = frames[self.index][1]
        while self.elapsed >= dur:
            self.elapsed -= dur
            self.index = (self.index + 1) % len(frames)
            dur = frames[self.index][1]

    def path(self):
        return self.anims[self.name][self.index][0]

    def all_paths(self):
        seen = []
        for frames in self.anims.values():
            for path, _dur in frames:
                if path not in seen:
                    seen.append(path)
        return seen

    def draw(self, ctx, x, y, size, flip_x=False, sx=1.0, sy=1.0):
        """Draw centred at (x, y). size = square canvas edge in px."""
        half = size / 2
        ctx.save()
        ctx.translate(x, y)
        ctx.scale(-sx if flip_x else sx, sy)
        ctx.image_smoothing = 0
        ctx.image(self.path(), -half, -half, size, size)
        ctx.restore()
