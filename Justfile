# spaceagon-mono dev entry points. Requires: uv (https://docs.astral.sh/uv/), just.

default:
    @just --list

# Lint + format check
lint:
    uv run ruff check .
    uv run ruff format --check .

# Auto-fix lint + format
fix:
    uv run ruff check --fix .
    uv run ruff format .

# Run the CPython unit tests (physics, cat brain, input layer, theme, flags)
test:
    uv run pytest -q

# Regenerate the cat sprite PNGs (deterministic)
assets skin="default":
    uv run python tools/gen_cat_sprites.py --skin {{skin}}

# Vendor shared libs into an app folder
vendor app:
    uv run python tools/vendor.py {{app}}

# Sideload an app to a badge over USB (USB IN port; hold reboop 2s after)
deploy app:
    uv run python tools/deploy.py {{app}}

# Run an app in the official simulator (needs Python 3.10; WASD = tilt, a-f = buttons)
sim app:
    python3.10 tools/sim.py {{app}}

# Headless one-frame smoke test of an app in the simulator
sim-smoke app:
    python3.10 tools/sim.py {{app}} --screenshot
