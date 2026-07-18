"""Locate an app's asset directory across all three runtimes.

ctx.image() requires absolute VFS paths. Install locations differ:
- badge sideload:  /apps/<folder>/
- badge app store: /apps/<owner>_<repo>/  (dashes flattened to underscores)
- simulator:       sim/apps/<folder>/ on the host filesystem
"""


def app_root(marker):
    """Return the app folder path whose name contains `marker`.

    Tries __file__ first (works in the simulator and on modern MicroPython),
    then scans /apps (store installs where the folder name is owner_repo).
    """
    try:
        here = __file__
        # .../<app>/spmono/util/assets.py -> .../<app>
        parts = here.replace("\\", "/").split("/")
        for i in range(len(parts) - 1, -1, -1):
            if marker in parts[i]:
                return "/".join(parts[: i + 1])
    except NameError:
        pass
    try:
        import os

        for entry in os.listdir("/apps"):
            if marker in entry:
                return "/apps/" + entry
    except OSError:
        pass
    return "/apps/" + marker  # last resort


def asset_path(marker, relative):
    return app_root(marker) + "/assets/" + relative
