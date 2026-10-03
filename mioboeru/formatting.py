# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Render matches for the destination field, e.g. `なん：非<b>難</b>、<b>難</b>解`."""

from collections.abc import Mapping, Sequence

from .matching import Match

WORD_SEPARATOR = "、"
LINE_SEPARATOR = "<br>"


def bold_kanji(surface: str, kanji: str) -> str:
    return surface.replace(kanji, f"<b>{kanji}</b>")


DEFAULT_WORD_TEMPLATE = "{word}"


# Templates use plain replace rather than str.format: a stray brace in user config must not raise.


def line_prefix(template: str, kanji: str, reading: str) -> str:
    return template.replace("{reading}", reading).replace("{kanji}", kanji)


def format_word(template: str, match: Match) -> str:
    word = bold_kanji(match.word.surface, match.unit)

    return template.replace("{reading}", match.word.reading).replace("{word}", word)


def format_matches(
    matches: Mapping[str, Sequence[Match]],
    prefix_template: str,
    word_template: str = DEFAULT_WORD_TEMPLATE,
) -> str:
    """
    One line per kanji of the target word, in the order the kanji appear in it.
    If a kanji's matches share different readings with the target, each reading gets its own line.
    """
    lines = []

    for kanji, kanji_matches in matches.items():
        by_reading: dict[str, list[Match]] = {}

        for match in kanji_matches:
            by_reading.setdefault(match.reading, []).append(match)

        for reading, group in by_reading.items():
            words = WORD_SEPARATOR.join(format_word(word_template, match) for match in group)
            lines.append(line_prefix(prefix_template, kanji, reading) + words)

    return LINE_SEPARATOR.join(lines)
