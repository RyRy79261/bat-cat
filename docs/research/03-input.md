# Buttons & input — the full API surface

> Research snapshot: 2026-07-18, verified line-by-line against
> `emfcamp/badge-2024-software` @ `beef903` (2026-07-16). This is the foundation for our
> input-abstraction layer.

## The one event vocabulary

**Every input on both badge generations — 2024 buttons, 2026 buttons A–F, joystick, touch
pads, proximity sensors — arrives as `ButtonDownEvent` / `ButtonUpEvent`** (from
`events.input`), each carrying a single `button` attribute. There is no separate
joystick/touch API.

`Button` objects (name, group, parents) form a hierarchy, and `Button.__contains__` walks
the parent chain — so the canonical check is membership:

```python
if BUTTON_TYPES["CONFIRM"] in event.button:   # matches 2024 button C, 2026 button C, AND joystick fire
```

## The button dictionaries (all plain dicts, not enums)

| Dict | Module | Keys | Group | Matches |
|---|---|---|---|---|
| `BUTTON_TYPES` | `events.input` | `UP DOWN LEFT RIGHT CONFIRM CANCEL UNDEFINED` | System | Abstract — works on 2024 + 2026, buttons + joystick. **Target this for portable bindings.** |
| `FRONTBOARD_BUTTON_TYPES` | `frontboards.common` | `A B C D E F` | Frontboard | Physical buttons only (both years) |
| `JOYSTICK_BUTTON_TYPES` | `events.joystick` | `UP DOWN LEFT RIGHT SELECT` (+unused `A B C X Y Z`) | Joystick | Joystick only |
| `TOUCH` | `frontboards.twentysix` | `TOUCH01`…`TOUCH12` | TwentyTwentySix | 2026 touch ring only |
| `PROX` | `frontboards.twentysix` | `LEFTPROX RIGHTPROX` | TwentyTwentySix | 2026 proximity only |

### 2026 physical mapping

- Buttons: **A→UP, B→RIGHT, C→CONFIRM, D→DOWN, E→LEFT, F→CANCEL** (each also parented to
  its `FRONTBOARD_BUTTON_TYPES` letter). Identical scheme on the 2024 board, so
  `BUTTON_TYPES` code is portable.
- Joystick: `JOYUP/JOYDOWN/JOYLEFT/JOYRIGHT/JOYFIRE`, each parented to **both** the matching
  `BUTTON_TYPES` direction (FIRE→CONFIRM) and `JOYSTICK_BUTTON_TYPES`.
  **⚠ Nothing on the joystick maps to CANCEL** — exit must come from button F or app logic.
- `TOUCH01–12` (clock layout, one pad per ring LED) and `LEFTPROX/RIGHTPROX` have **no
  parents** — they never match `BUTTON_TYPES` checks; match by dict membership or
  `event.button.name`. ⚠ The docs page writes `TOUCH1`…`TOUCH12`; the actual code
  identifiers are **zero-padded** (`TOUCH01`).

Also legal: substring matching, e.g. `if "FIRE" in event.button.name:`.

## Two consumption styles

**Polling — `Buttons` helper** (self-subscribes to the eventbus):

```python
from events.input import Buttons, BUTTON_TYPES

def __init__(self):
    super().__init__()
    self.button_states = Buttons(self)

def update(self, delta):
    if self.button_states.get(BUTTON_TYPES["CANCEL"]):   # True while held
        self.button_states.clear()
        self.minimise()
    if self.button_states.pressed(BUTTON_TYPES["CONFIRM"]):  # latched: True once per press
        ...
```

**Event-driven — eventbus subscription:**

```python
from system.eventbus import eventbus
from events.input import ButtonDownEvent

def __init__(self):
    super().__init__()
    eventbus.on(ButtonDownEvent, self._on_down, self)   # or on_async

def _on_down(self, event):
    if BUTTON_TYPES["CONFIRM"] in event.button: ...
```

⚠ Pass the **same app object** to `eventbus.remove(...)` that you registered with (handlers
are keyed per-app; the official test app gets this wrong by passing `None`). Handlers are
auto-removed on app *stop*, not on *minimise*.

## Semantics an abstraction layer must handle

- **Auto-repeat**: held physical buttons and joystick directions re-emit `ButtonDownEvent`
  every **200 ms** on the 2026 board (2024: ~100 ms after ~500 ms hold). A Down event is
  therefore NOT a fresh press — do edge detection (as `Buttons.pressed()` does) before
  layering long-press logic.
- **Touch/prox do NOT auto-repeat** — one Down on contact, one Up on release. Binary only;
  no analog/pressure values are exposed to apps.
- **No framework long-press / chord / gesture support.** The official Spaceagon test app
  implements a C+D chord by hand with two booleans. This is exactly the gap our shared input
  library should fill.
- **Focus**: input events have `requires_focus = True`; only the app on top of the
  scheduler's `foreground_stack` receives them (exactly one app at a time). Overlay apps
  ("on top" stack) can draw but never get focus. You can't read buttons while minimised.
- **Exit convention**: CANCEL (button F) → `self.minimise()`. Documented as "you should
  always provide a way to get out" — a convention, not enforced review (there is no review).

## Frontboard detection

```python
from frontboards.utils import detect_frontboard   # NB: docs typo says "frontboard.utils"
board = detect_frontboard()   # 0x26XX = Spaceagon (0x2600/0x2601 revs), 0x2400 = 2024 board
```

Guard `from frontboards.twentysix import TOUCH, PROX` imports if you want to keep 2024
compatibility (touch/prox/joystick simply never fire on a 2024 board; compass returns
stale/zero).

## Compass is not an input event

`imu.mag_read()` → `(x, y, z)` floats in gauss — see `04-sensors-and-peripherals.md`.

## Design implications for our input layer (bat-cat)

1. Normalize on `(event.button.name, group, parents)` — one vocabulary covers everything.
2. Bindings should target `BUTTON_TYPES` by default (portable), with opt-in
   joystick/frontboard/touch-specific bindings.
3. We must own: edge detection (debounce of the 200 ms auto-repeat), long-press, chords,
   repeat-with-acceleration, and "action map" composition (assign semantic actions to
   physical inputs per app).
4. Always ship a CANCEL→minimise default binding so every composed app has an exit.

## Key sources

- `modules/events/input.py`, `modules/events/joystick.py`, `modules/frontboards/common.py`,
  `modules/frontboards/twentysix.py`, `modules/system/eventbus.py`,
  `modules/system/scheduler/__init__.py`, `modules/app.py` — all in
  <https://github.com/emfcamp/badge-2024-software>
- <https://tildagon.badge.emfcamp.org/tildagon-apps/reference/spaceagon/>
- Official 2026 input example: <https://github.com/emfcamp/badge-2026-apps-spaceagon-test>
