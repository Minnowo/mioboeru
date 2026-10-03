# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""
Decide whether two words share a kanji *with the same reading*.

Matchers are pluggable (see MATCHERS / make_matcher) so a dictionary-based matcher can be
added next to the reading-only "dumb" one and chosen from the config.
"""

import abc
import enum
from collections import Counter
from collections.abc import Iterable, Sequence
from typing import NamedTuple, Optional

from .furigana import Word, is_kanji, to_hiragana

# A kanji's reading never starts with these, so a split point in front of one is impossible.
_CANNOT_START = frozenset("ぁぃぅぇぉゃゅょゎっんー")
# Kana that become っ when a kanji's reading is shortened (学 がく -> 学校 がっこう).
_GEMINATES = frozenset("つくちき")
_UNVOICE = str.maketrans(
    "がぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽゔ",
    "かきくけこさしすせそたちつてとはひふへほはひふへほう",
)


def kana_close(a: str, b: str) -> bool:
    """Equal up to voicing (き/ぎ, ほ/ぼ/ぽ) or gemination (つ/っ, く/っ)."""
    if a.translate(_UNVOICE) == b.translate(_UNVOICE):
        return True

    return (a == "っ" and b in _GEMINATES) or (b == "っ" and a in _GEMINATES)


def _common_prefix(a: str, b: str) -> str:
    n = 0

    while n < min(len(a), len(b)) and a[n] == b[n]:
        n += 1

    return a[:n]


def _common_suffix(a: str, b: str) -> str:
    return _common_prefix(a[::-1], b[::-1])[::-1]


class Anchor(enum.Enum):
    START = enum.auto()
    END = enum.auto()


class WordCore(NamedTuple):
    """A word with the kana it shares with its reading at either edge removed (お茶 -> 茶, 暮らし -> 暮)."""

    surface: str
    reading: str

    @classmethod
    def from_word(cls, word: Word) -> Optional["WordCore"]:
        surface, reading = word.surface, word.reading

        while surface and reading and to_hiragana(surface[0]) == reading[0]:
            surface, reading = surface[1:], reading[1:]

        while surface and reading and to_hiragana(surface[-1]) == reading[-1]:
            surface, reading = surface[:-1], reading[:-1]

        if not surface or not reading:
            return None

        return cls(surface, reading)

    def anchors(self, unit: str) -> list[Anchor]:
        """Edges of the word where `unit` (a kanji or a run of characters) sits."""
        anchors = []

        if self.surface.startswith(unit):
            anchors.append(Anchor.START)

        if self.surface.endswith(unit):
            anchors.append(Anchor.END)

        return anchors

    def neighbour(self, anchor: Anchor, unit: str) -> Optional[str]:
        """The character right next to `unit` on the inner side, if any."""
        rest = self.surface[len(unit) :] if anchor == Anchor.START else self.surface[: len(self.surface) - len(unit)]

        if not rest:
            return None

        return rest[0] if anchor == Anchor.START else rest[-1]

    def segment_lengths(self, unit: str) -> Sequence[int]:
        """Possible lengths of the edge unit's reading, longest first."""
        if self.surface == unit:
            return (len(self.reading),)

        # Every character needs at least one kana of the reading.
        return range(len(self.reading) - (len(self.surface) - len(unit)), len(unit) - 1, -1)

    def segment(self, anchor: Anchor, length: int) -> Optional[str]:
        """The first or last `length` kana of the reading, or None if that split is impossible."""
        if anchor == Anchor.START:
            seg, rest = self.reading[:length], self.reading[length:]

            if rest and rest[0] in _CANNOT_START:
                return None
        else:
            seg = self.reading[len(self.reading) - length :]

        if not seg or seg[0] in _CANNOT_START:
            return None

        return seg


class ReadingMatcher(abc.ABC):
    @abc.abstractmethod
    def shared_reading(self, a: Word, b: Word, kanji: str) -> Optional[str]:
        """Return the reading `kanji` has in both words (as spelled in `a`), or None."""
        raise NotImplementedError()

    @abc.abstractmethod
    def shared_run(self, a: Word, b: Word) -> Optional[tuple[str, str]]:
        """
        If the words share a run of 2+ characters read the same way (問題 in 問題集, 日本 in
        日本人/日本語), return (run, reading as spelled in `a`). Per-kanji readings inside a shared
        run can't be told apart from the two words alone, so the run is matched as a whole.
        """
        raise NotImplementedError()


class DumbMatcher(ReadingMatcher):
    """
    Uses whole-word readings only. Works when the kanji is the first or last kanji of both
    words: compares the start/end of the readings. Kanji in the middle of a word are skipped.

    A single-kanji word's whole reading is the kanji's reading, so it may match with fewer than
    `min_shared_kana` kana (気[き] <-> 天気[てんき]).
    """

    def __init__(self, min_shared_kana: int = 2, fuzzy_kana: bool = True) -> None:
        self._min_shared_kana = min_shared_kana
        self._fuzzy_kana = fuzzy_kana

    def shared_reading(self, a: Word, b: Word, kanji: str) -> Optional[str]:
        core_a, core_b = WordCore.from_word(a), WordCore.from_word(b)

        if core_a is None or core_b is None:
            return None

        best: Optional[str] = None

        for anchor_a in core_a.anchors(kanji):
            for anchor_b in core_b.anchors(kanji):
                neighbour = core_a.neighbour(anchor_a, kanji)

                if anchor_a == anchor_b and neighbour is not None and neighbour == core_b.neighbour(anchor_b, kanji):
                    # Same next character on the same side (問題 / 問題集): the shared reading would
                    # spill into it. shared_run() handles this case.
                    continue

                seg = self._match_at(core_a, anchor_a, core_b, anchor_b, kanji)

                if seg and (best is None or len(seg) > len(best)):
                    best = seg

        return best

    def shared_run(self, a: Word, b: Word) -> Optional[tuple[str, str]]:
        core_a, core_b = WordCore.from_word(a), WordCore.from_word(b)

        if core_a is None or core_b is None or core_a.surface == core_b.surface:
            return None

        for run, anchor in (
            (_common_prefix(core_a.surface, core_b.surface), Anchor.START),
            (_common_suffix(core_a.surface, core_b.surface), Anchor.END),
        ):
            if len(run) >= 2 and any(is_kanji(char) for char in run):
                if seg := self._match_at(core_a, anchor, core_b, anchor, run):
                    return run, seg

        return self._contained_run(core_a, core_b)

    def _contained_run(self, a: WordCore, b: WordCore) -> Optional[tuple[str, str]]:
        """One word sits in the middle of the other (問題 in 大問題集)."""
        short, long = (a, b) if len(a.surface) <= len(b.surface) else (b, a)

        if len(short.surface) < 2 or short.surface not in long.surface[1:-1]:
            return None

        width = len(short.reading)

        for start in range(1, len(long.reading) - width):
            window = long.reading[start : start + width]

            if window[0] not in _CANNOT_START and self._fuzzy_equal(short.reading, window, {0, width - 1}):
                return short.surface, (short.reading if short is a else window)

        return None

    def _match_at(self, a: WordCore, anchor_a: Anchor, b: WordCore, anchor_b: Anchor, unit: str) -> Optional[str]:
        lengths_b = frozenset(b.segment_lengths(unit))
        whole_word = a.surface == unit or b.surface == unit

        for length in a.segment_lengths(unit):
            if length not in lengths_b:
                continue

            seg_a, seg_b = a.segment(anchor_a, length), b.segment(anchor_b, length)

            if seg_a is None or seg_b is None or not self._segments_equal(seg_a, anchor_a, seg_b, anchor_b):
                continue

            if length >= self._min_shared_kana or whole_word:
                return seg_a

            return None  # longest match is too short; shorter ones would be too

        return None

    def _segments_equal(self, a: str, anchor_a: Anchor, b: str, anchor_b: Anchor) -> bool:
        # Sound changes happen where the unit meets the next character, i.e. at the inner edge.
        return self._fuzzy_equal(a, b, {self._inner_index(a, anchor_a), self._inner_index(b, anchor_b)})

    def _fuzzy_equal(self, a: str, b: str, fuzzy_positions: set[int]) -> bool:
        return all(
            ca == cb or (self._fuzzy_kana and idx in fuzzy_positions and kana_close(ca, cb))
            for idx, (ca, cb) in enumerate(zip(a, b))
        )

    @staticmethod
    def _inner_index(seg: str, anchor: Anchor) -> int:
        return len(seg) - 1 if anchor == Anchor.START else 0


MATCHERS = {
    "dumb": DumbMatcher,
}


def make_matcher(method: str, min_shared_kana: int, fuzzy_kana: bool) -> ReadingMatcher:
    try:
        matcher_cls = MATCHERS[method]
    except KeyError:
        raise ValueError(f"Unknown match method '{method}'. Available: {', '.join(MATCHERS)}.")

    return matcher_cls(min_shared_kana=min_shared_kana, fuzzy_kana=fuzzy_kana)


class Match(NamedTuple):
    unit: str  # a kanji of the target word, or a run of characters shared with it (問題)
    reading: str  # the unit's reading as spelled in the target word
    word: Word


class KanjiIndex:
    """Words grouped by the kanji they contain. Duplicate words are stored once."""

    def __init__(self, words: Iterable[Word] = ()) -> None:
        self._by_kanji: dict[str, dict[Word, None]] = {}

        for word in words:
            self.add(word)

    def add(self, word: Word) -> None:
        for char in word.surface:
            if is_kanji(char):
                self._by_kanji.setdefault(char, {})[word] = None

    def words_with(self, kanji: str) -> Iterable[Word]:
        return self._by_kanji.get(kanji, {}).keys()


def settle_readings(matches: Sequence[Match]) -> list[Match]:
    """
    A kanji's reading guessed from one word pair can spill into the next kanji (学生 <-> 学説 share
    がくせ). When a shorter reading on the same edge is supported by at least as many matches
    (学校, 大学 -> がく), relabel the longer one with it.
    """
    counts = Counter(match.reading for match in matches)
    by_length = sorted(counts, key=len)

    def settle(reading: str) -> str:
        for shorter in by_length:
            if len(shorter) >= len(reading):
                break

            if counts[shorter] >= counts[reading] and (reading.startswith(shorter) or reading.endswith(shorter)):
                return shorter

        return reading

    return [match._replace(reading=settle(match.reading)) for match in matches]


def find_matches(
    target: Word,
    index: KanjiIndex,
    matcher: ReadingMatcher,
    max_per_unit: int,
) -> dict[str, list[Match]]:
    """
    Words sharing a kanji reading with `target`, keyed by the kanji (in the order they appear in
    the target), followed by runs of 2+ characters shared as a whole (問題 -> 問題集).
    """
    kanji_list = list(dict.fromkeys(char for char in target.surface if is_kanji(char)))
    per_kanji: dict[str, list[Match]] = {kanji: [] for kanji in kanji_list}
    runs: dict[str, list[Match]] = {}
    candidates = dict.fromkeys(word for kanji in kanji_list for word in index.words_with(kanji))

    for word in candidates:
        if word.surface == target.surface:
            continue

        if shared := matcher.shared_run(target, word):
            run, reading = shared
            runs.setdefault(run, []).append(Match(run, reading, word))

        for kanji in kanji_list:
            if kanji in word.surface and (reading := matcher.shared_reading(target, word, kanji)) is not None:
                per_kanji[kanji].append(Match(kanji, reading, word))

    result = {kanji: settle_readings(matches) for kanji, matches in per_kanji.items()}
    result.update(runs)

    return {unit: matches[:max_per_unit] for unit, matches in result.items() if matches}
