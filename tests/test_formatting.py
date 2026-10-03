# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from mioboeru.formatting import bold_kanji, format_matches
from mioboeru.furigana import parse_furigana
from mioboeru.matching import DumbMatcher, KanjiIndex, Match, find_matches


def test_bold_kanji() -> None:
    assert bold_kanji("難点", "難") == "<b>難</b>点"
    assert bold_kanji("時々", "時") == "<b>時</b>々"


def test_format_matches() -> None:
    fields = [
        "非難[ひなん]",
        "無難[ぶなん]",
        "難解[なんかい]",
        "難点[なんてん]",
        "難問[なんもん]",
        "問題[もんだい]",
        "話題[わだい]",
    ]
    index = KanjiIndex(word for word in map(parse_furigana, fields) if word)
    target = parse_furigana("難題[なんだい]")
    assert target
    result = find_matches(target, index, DumbMatcher(), max_per_unit=10)
    assert format_matches(result, "{reading}：") == (
        "なん：非<b>難</b>、無<b>難</b>、<b>難</b>解、<b>難</b>点、<b>難</b>問"
        + "<br>"
        + "だい：問<b>題</b>、話<b>題</b>"
    )
    assert format_matches(result, "読み覚え：").startswith("読み覚え：非<b>難</b>")
    assert format_matches(result, "{kanji}（{reading}）").startswith("難（なん）非<b>難</b>")


def test_format_shows_target_reading_for_fuzzy_match() -> None:
    target = parse_furigana("学生[がくせい]")
    assert target
    words = [parse_furigana(f) for f in ("学校[がっこう]", "大学[だいがく]", "学者[がくしゃ]")]
    index = KanjiIndex(word for word in words if word)
    result = find_matches(target, index, DumbMatcher(), max_per_unit=10)
    assert format_matches(result, "{reading}：") == (
        "がく：<b>学</b>校、大<b>学</b>、<b>学</b>者"  # 学校 matched via がく <-> がっ, shown as the target's がく
    )


def test_format_splits_lines_by_reading() -> None:
    def match(reading: str, field: str) -> Match:
        word = parse_furigana(field)
        assert word
        return Match("日", reading, word)

    matches = {"日": [match("にち", "毎日[まいにち]"), match("ひ", "日[ひ]"), match("にち", "日曜[にちよう]")]}
    assert format_matches(matches, "{reading}：") == "にち：毎<b>日</b>、<b>日</b>曜<br>ひ：<b>日</b>"


def test_format_tolerates_braces() -> None:
    assert format_matches({}, "{oops}") == ""


def test_format_shared_run() -> None:
    target = parse_furigana("問題[もんだい]")
    assert target
    words = [parse_furigana(f) for f in ("質問[しつもん]", "問題集[もんだいしゅう]")]
    result = find_matches(target, KanjiIndex(word for word in words if word), DumbMatcher(), max_per_unit=10)
    assert format_matches(result, "{reading}：") == "もん：質<b>問</b><br>もんだい：<b>問題</b>集"


def test_word_template() -> None:
    def match(unit: str, reading: str, field: str) -> Match:
        word = parse_furigana(field)
        assert word
        return Match(unit, reading, word)

    matches = {
        "分": [
            match("分", "ぶん", "部分[ぶぶん]"),
            match("分", "ぶん", "分[ぶん]"),
            match("分", "ぶん", "申[もう]し 分[ぶん]ない"),
        ]
    }
    assert format_matches(matches, "{reading}：", "{word}({reading})") == (
        "ぶん：部<b>分</b>(ぶぶん)、<b>分</b>(ぶん)、申し<b>分</b>ない(もうしぶんない)"
    )
    assert format_matches(matches, "", "{word}") == "部<b>分</b>、<b>分</b>、申し<b>分</b>ない"
    assert format_matches(matches, "", "<ruby>{word}<rt>{reading}</rt></ruby>").startswith(
        "<ruby>部<b>分</b><rt>ぶぶん</rt></ruby>、"
    )
