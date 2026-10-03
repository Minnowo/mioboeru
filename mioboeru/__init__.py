# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import sys

try:
    from aqt import mw
except ImportError:
    mw = None  # imported outside Anki, e.g. by tests


def start_addon() -> None:
    from . import gui
    from .config import MioboeruConfig

    config = MioboeruConfig()

    assert mw

    mw.addonManager.setConfigUpdatedAction(__name__, config.update_from_addon_manager)

    gui.init(config)


if mw and "pytest" not in sys.modules:
    start_addon()
