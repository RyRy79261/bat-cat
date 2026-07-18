import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Import spmono straight from libs/ (its internal imports are all relative).
sys.path.insert(0, str(ROOT / "libs"))


def _load(name, path):
    # Load pure-logic app modules directly from file, bypassing the app
    # package __init__ (which pulls in firmware modules like imu).
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_load("cat_yarn_cats", str(ROOT / "apps" / "cat_yarn" / "cats.py"))
_load("cat_yarn_planets", str(ROOT / "apps" / "cat_yarn" / "planets.py"))
