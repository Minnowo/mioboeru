# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Parse Anki furigana fields (e.g. `異様[いよう]`, `一人暮[ひとりぐ]らし`) into surface + reading."""

import re
from typing import NamedTuple, Optional

_HTML_TAG = re.compile(r"<[^>]*>")
# Same shape as the regex behind Anki's {{kanji:}} / {{kana:}} template filters.
_FURIGANA = re.compile(r" ?([^ >\[\]]+?)\[([^\]]+)\]")

_KATAKANA_TO_HIRAGANA = {code: code - 0x60 for code in range(ord("ァ"), ord("ヶ") + 1)}


class Word(NamedTuple):
    surface: str  # 宿題
    reading: str  # しゅくだい (always hiragana)


def to_hiragana(text: str) -> str:
    return text.translate(_KATAKANA_TO_HIRAGANA)


def is_kanji(char: str) -> bool:
    return "\u4e00" <= char <= "\u9fff" or "\u3400" <= char <= "\u4dbf" or "\uf900" <= char <= "\ufaff"


def is_kana(char: str) -> bool:
    return "\u3041" <= char <= "\u309f" or "\u30a0" <= char <= "\u30ff"


def parse_furigana(field: str) -> Optional[Word]:
    """Return the word and its reading, or None if the field has no usable reading."""
    text = _HTML_TAG.sub("", field).replace("&nbsp;", " ").strip()

    surface = _FURIGANA.sub(r"\1", text).replace(" ", "")
    reading = to_hiragana(_FURIGANA.sub(r"\2", text).replace(" ", ""))

    if not surface or not reading or not all(is_kana(char) for char in reading):
        return None

    return Word(surface, reading)
