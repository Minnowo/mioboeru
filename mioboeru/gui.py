# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from collections.abc import Callable, Sequence

from anki.collection import Collection
from anki.notes import NoteId
from aqt import gui_hooks, mw
from aqt.browser import Browser
from aqt.editor import Editor
from aqt.operations import CollectionOp
from aqt.qt import QAction, QMenu, QWidget, qconnect
from aqt.utils import tooltip

from .ajt_common.about_menu import menu_root_entry
from .ajt_common.addon_config import set_config_action
from .config import MioboeruConfig
from .operations import ADDON_NAME, fill_note_op, fill_related_op, target_search
from .settings_dialog import MioboeruSettingsDialog

ACTION_NAME = f"{ADDON_NAME}: Fill related words"


def run_fill(parent: QWidget, config: MioboeruConfig, get_nids: Callable[[Collection], Sequence[NoteId]]) -> None:
    CollectionOp(
        parent=parent,
        op=lambda col: fill_related_op(col, get_nids(col), config),
    ).success(
        lambda out: tooltip(f"{ADDON_NAME}: updated {out.count} notes.", parent=parent),
    ).run_in_background()


def fill_target_decks(config: MioboeruConfig) -> None:
    assert mw

    run_fill(mw, config, lambda col: col.find_notes(target_search(col, config)))


def fill_selected(browser: Browser, config: MioboeruConfig) -> None:
    nids = browser.selected_notes()  # read on the main thread; the op runs in the background

    run_fill(browser, config, lambda col: nids)


def open_settings(config: MioboeruConfig) -> None:
    assert mw

    MioboeruSettingsDialog(config, mw).exec()


def add_action(menu: QMenu, text: str, on_triggered: Callable[[], None]) -> None:
    action = QAction(text, menu)

    qconnect(action.triggered, on_triggered)

    menu.addAction(action)


def setup_ajt_menu(config: MioboeruConfig) -> None:
    """AJT > Mioboeru submenu, shared with other Ajatt-Tools add-ons."""
    menu = menu_root_entry().addMenu(ADDON_NAME)

    assert menu

    add_action(menu, "Options...", lambda: open_settings(config))
    add_action(menu, "Fill related words (target decks)", lambda: fill_target_decks(config))


def setup_browser_menu(browser: Browser, config: MioboeruConfig) -> None:
    action = QAction(f"{ACTION_NAME} (selected notes)", browser)

    qconnect(action.triggered, lambda: fill_selected(browser, config))

    browser.form.menuEdit.addAction(action)


def fill_current_note(editor: Editor, config: MioboeruConfig) -> None:
    def run() -> None:
        if (note := editor.note) is None:
            return

        CollectionOp(
            parent=editor.widget,
            op=lambda col: fill_note_op(col, note, config),
        ).success(
            lambda out: editor.loadNoteKeepingFocus(),
        ).run_in_background()

    # Save what the user is typing first, so the reading field is up to date.
    editor.call_after_note_saved(run, keepFocus=True)


def add_editor_button(buttons: list[str], editor: Editor, config: MioboeruConfig) -> None:
    buttons.append(
        editor.addButton(
            icon=None,
            cmd="ajt__mioboeru_fill_note",
            func=lambda ed: fill_current_note(ed, config),
            tip=f"{ADDON_NAME}: fill related words in this note",
            label="読",
        )
    )


def init(config: MioboeruConfig) -> None:
    setup_ajt_menu(config)

    set_config_action(lambda: open_settings(config))  # Tools > Add-ons > Config opens the same dialog

    gui_hooks.browser_menus_did_init.append(lambda browser: setup_browser_menu(browser, config))
    gui_hooks.editor_did_init_buttons.append(lambda buttons, editor: add_editor_button(buttons, editor, config))
