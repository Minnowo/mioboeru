# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from collections.abc import Iterable, Sequence

from aqt import mw
from aqt.qt import (
    QCheckBox,
    QComboBox,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPalette,
    QSpinBox,
    Qt,
    QVBoxLayout,
    QWidget,
    qconnect,
)

from .ajt_common.about_menu import tweak_window
from .ajt_common.anki_field_selector import AnkiFieldSelector
from .ajt_common.checkable_combobox import CheckableComboBox
from .ajt_common.restore_geom_dialog import AnkiSaveAndRestoreGeomDialog
from .config import MioboeruConfig
from .formatting import format_matches
from .furigana import Word
from .matching import MATCHERS, Match
from .operations import ADDON_NAME


def note_type_names() -> Iterable[str]:
    assert mw and mw.col

    return (note_type.name for note_type in mw.col.models.all_names_and_ids())


def deck_names() -> Iterable[str]:
    assert mw and mw.col

    return (deck.name for deck in mw.col.decks.all_names_and_ids())


def checkable_combo(available: Iterable[str], checked: Sequence[str]) -> CheckableComboBox:
    combo = CheckableComboBox()

    # Keep configured names that no longer exist so saving doesn't silently drop them.
    combo.setCheckableTexts(dict.fromkeys([*available, *checked]))
    combo.setCheckedTexts(checked)

    return combo


LINE_PREFIX_HELP = (
    "<b>{reading}</b> -> the kanji's reading in this word (なん)<br>"
    "<b>{kanji}</b> -> the kanji itself (難)<br>"
    "Other text is kept as is."
)

WORD_TEMPLATE_HELP = (
    "<b>{word}</b> -> the matched word, shared kanji in bold (非<b>難</b>)<br>"
    "<b>{reading}</b> -> the matched word's reading (ひなん)<br>"
    "e.g. {word}({reading}) -> 非<b>難</b>(ひなん)"
)

# Matches for 難題, used to preview the destination field.
PREVIEW_TARGET = "難題"

PREVIEW_MATCHES = {
    "難": [
        Match("難", "なん", Word("非難", "ひなん")),
        Match("難", "なん", Word("難点", "なんてん")),
    ],
    "題": [
        Match("題", "だい", Word("問題", "もんだい")),
        Match("題", "だい", Word("話題", "わだい")),
    ],
}


def muted_label(text: str) -> QLabel:
    label = QLabel(text)  # no word wrap: wrapped labels get clipped inside QFormLayout

    label.setTextFormat(Qt.TextFormat.RichText)
    label.setForegroundRole(QPalette.ColorRole.PlaceholderText)

    return label


def spin_box(value: int, minimum: int, maximum: int) -> QSpinBox:
    box = QSpinBox()

    box.setRange(minimum, maximum)
    box.setValue(value)

    return box


def check_box(text: str, checked: bool) -> QCheckBox:
    box = QCheckBox(text)

    box.setChecked(checked)

    return box


class MioboeruSettingsDialog(AnkiSaveAndRestoreGeomDialog):
    name: str = "ajt__mioboeru_options"

    def __init__(self, config: MioboeruConfig, parent: QWidget) -> None:
        super().__init__(parent)

        self._config = config

        # Notes
        self._note_types = checkable_combo(note_type_names(), config.note_types)
        self._target_decks = checkable_combo(deck_names(), config.target_decks)
        self._reading_field = AnkiFieldSelector(config.reading_field)
        self._destination_field = AnkiFieldSelector(config.destination_field)

        self._search_query = QLineEdit(config.search_query)
        self._search_query.setPlaceholderText("e.g. deck:Japanese -is:new")

        self._overwrite = check_box("Overwrite non-empty destination field", config.overwrite_destination)

        # Output
        self._line_prefix = QLineEdit(config.line_prefix_template)
        self._line_prefix_help = muted_label(LINE_PREFIX_HELP)

        self._word_template = QLineEdit(config.word_template)
        self._word_template_help = muted_label(WORD_TEMPLATE_HELP)

        self._preview = QLabel()
        self._preview.setTextFormat(Qt.TextFormat.RichText)
        self._update_preview()

        self._max_matches = spin_box(config.max_matches, 1, 999)

        # Matching
        self._match_method = QComboBox()
        self._match_method.addItems(MATCHERS)
        self._match_method.setCurrentText(config.match_method)

        self._min_shared_kana = spin_box(config.min_shared_kana, 1, 10)
        self._fuzzy_kana = check_box("Allow sound changes (き/ぎ, つ/っ)", config.fuzzy_kana)

        self._button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)

        self._add_tooltips()
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowTitle(f"{ADDON_NAME} - Options")
        self.setMinimumWidth(480)
        tweak_window(self)

        notes = QFormLayout()
        notes.addRow("Note types", self._note_types)
        notes.addRow("Target decks", self._target_decks)
        notes.addRow("Reading field", self._reading_field)
        notes.addRow("Destination field", self._destination_field)
        notes.addRow("Match source filter", self._search_query)
        notes.addRow(self._overwrite)

        output = QFormLayout()
        output.addRow("Line prefix", self._line_prefix)
        output.addRow("", self._line_prefix_help)
        output.addRow("Word format", self._word_template)
        output.addRow("", self._word_template_help)
        output.addRow(f"Example for {PREVIEW_TARGET}", self._preview)
        output.addRow("Max words per kanji", self._max_matches)

        matching = QFormLayout()
        matching.addRow("Method", self._match_method)
        matching.addRow("Min shared kana", self._min_shared_kana)
        matching.addRow(self._fuzzy_kana)

        layout = QVBoxLayout()
        for title, form in (("Notes", notes), ("Output", output), ("Matching", matching)):
            group = QGroupBox(title)
            group.setLayout(form)
            layout.addWidget(group)

        layout.addStretch()
        layout.addWidget(self._button_box)
        self.setLayout(layout)

        qconnect(self._line_prefix.textChanged, self._update_preview)
        qconnect(self._word_template.textChanged, self._update_preview)

        qconnect(self._button_box.accepted, self.accept)
        qconnect(self._button_box.rejected, self.reject)

    def _update_preview(self) -> None:
        self._preview.setText(format_matches(PREVIEW_MATCHES, self._line_prefix.text(), self._word_template.text()))

    def _add_tooltips(self) -> None:
        self._note_types.setToolTip("Note types to fill, and to search for related words.")

        self._target_decks.setToolTip(
            "Decks (with subdecks) filled by AJT > Mioboeru > Fill related words (target decks).\n"
            "Related words are still searched in all decks.\n"
            "Selected notes in the browser and the editor button ignore this."
        )

        self._reading_field.setToolTip("Field with the word and its reading, e.g. 宿題[しゅくだい].")

        self._destination_field.setToolTip("Field that receives the related words.")

        self._search_query.setToolTip(
            "Extra Anki search that narrows which notes can be listed as related words.\n"
            "Doesn't change which notes get filled. Empty means no extra filter."
        )

        self._overwrite.setToolTip(
            "Off: bulk runs skip notes that already have related words.\n"
            "On: refresh them, e.g. after adding new cards.\n"
            "The editor button always overwrites."
        )

        self._line_prefix.setToolTip(
            "Text at the start of each line, one line per kanji.\n"
            "{reading}: the kanji's reading in this word (hiragana), {kanji}: the kanji.\n"
            "Default: {reading}："
        )

        self._word_template.setToolTip(
            "How each matched word is written.\n"
            "{word}: the word with the shared kanji in bold, {reading}: its reading.\n"
            "Default: {word}"
        )

        self._max_matches.setToolTip("Maximum number of related words listed per kanji.")

        self._match_method.setToolTip("dumb: compare the start/end of whole-word readings, no dictionary.")

        self._min_shared_kana.setToolTip(
            "Shortest shared reading accepted.\n"
            "1 finds 天気 <-> 元気 (き) but also false matches like 時間 <-> 人間 (ん).\n"
            "Single-kanji words always count."
        )

        self._fuzzy_kana.setToolTip("Treat voicing and gemination where kanji meet as the same reading.")

    def accept(self) -> None:
        self._config["note_types"] = list(self._note_types.checkedTexts())
        self._config["target_decks"] = list(self._target_decks.checkedTexts())
        self._config["reading_field"] = self._reading_field.currentText().strip()
        self._config["destination_field"] = self._destination_field.currentText().strip()
        self._config["search_query"] = self._search_query.text().strip()
        self._config["overwrite_destination"] = self._overwrite.isChecked()
        self._config["line_prefix_template"] = self._line_prefix.text()
        self._config["word_template"] = self._word_template.text()
        self._config["max_matches"] = self._max_matches.value()
        self._config["match_method"] = self._match_method.currentText()
        self._config["min_shared_kana"] = self._min_shared_kana.value()
        self._config["fuzzy_kana"] = self._fuzzy_kana.isChecked()

        self._config.write_config()

        super().accept()
