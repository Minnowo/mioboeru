# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from typing import Optional

from mioboeru.furigana import Word, parse_furigana
from mioboeru.matching import DumbMatcher, KanjiIndex, Match, find_matches, make_matcher, settle_readings


def w(field: str) -> Word:
    word = parse_furigana(field)
    assert word is not None
    return word


def shared(a: str, b: str, kanji: str, matcher: Optional[DumbMatcher] = None) -> Optional[str]:
    return (matcher or DumbMatcher()).shared_reading(w(a), w(b), kanji)


def test_same_reading_at_edges() -> None:
    cases = [
        ("宿題[しゅくだい]", "問題[もんだい]", "題", "だい"),  # end <-> end
        ("宿題[しゅくだい]", "宿泊[しゅくはく]", "宿", "しゅく"),  # start <-> start
        ("問題[もんだい]", "題名[だいめい]", "題", "だい"),  # end <-> start
        ("日本人[にほんじん]", "外人[がいじん]", "人", "じん"),  # 3-kanji word, kanji at end
        ("一人暮[ひとりぐ]らし", "暮[く]らし", "暮", "ぐ"),  # okurigana stripped
        ("お 茶[ちゃ]", "緑茶[りょくちゃ]", "茶", "ちゃ"),
    ]
    for a, b, kanji, expected in cases:
        assert shared(a, b, kanji) == expected, (a, b)


def test_different_reading() -> None:
    cases = [
        ("時間[じかん]", "人間[にんげん]", "間"),  # only ん in common
        ("毎日[まいにち]", "今日[きょう]", "日"),
        ("上手[じょうず]", "下手[へた]", "手"),
        ("大人[おとな]", "恋人[こいびと]", "人"),
    ]
    for a, b, kanji in cases:
        assert shared(a, b, kanji) is None, (a, b)


def test_single_kanji_word_is_full_reading() -> None:
    assert shared("気[き]", "天気[てんき]", "気") == "き"
    assert shared("天気[てんき]", "元気[げんき]", "気") is None  # below min_shared_kana
    assert shared("天気[てんき]", "元気[げんき]", "気", DumbMatcher(min_shared_kana=1)) == "き"
    assert shared("本[ほん]", "日本[にほん]", "本") == "ほん"


def test_fuzzy_kana() -> None:
    assert shared("学生[がくせい]", "学校[がっこう]", "学") == "がく"  # く -> っ
    assert shared("一日[いちにち]", "一歩[いっぽ]", "一") == "いち"  # ち -> っ
    assert shared("日本[にほん]", "三本[さんぼん]", "本") == "ほん"  # ほ -> ぼ
    strict = DumbMatcher(fuzzy_kana=False)
    assert shared("学生[がくせい]", "学校[がっこう]", "学", strict) is None
    assert shared("日本[にほん]", "三本[さんぼん]", "本", strict) is None


def test_fuzzy_only_at_inner_edge() -> None:
    # The word-final kana must match exactly; voicing there is a different reading.
    assert shared("金[かね]", "金[かね]", "金") == "かね"
    assert shared("口[くち]", "入口[いりぐち]", "口") == "くち"  # rendaku on the inner edge
    assert shared("経理[けいり]", "経緯[けいい]", "経") == "けい"
    assert shared("家[か]", "画家[がか]", "家") == "か"
    assert shared("家[いえ]", "画家[がか]", "家") is None


def test_middle_kanji_skipped() -> None:
    assert shared("図書館[としょかん]", "書類[しょるい]", "書") is None


def test_find_matches() -> None:
    target = w("宿題[しゅくだい]")
    index = KanjiIndex(
        w(field)
        for field in (
            "宿題[しゅくだい]",
            "問題[もんだい]",
            "話題[わだい]",
            "宿泊[しゅくはく]",
            "宿屋[やどや]",
            "問題[もんだい]",
        )
    )
    result = find_matches(target, index, DumbMatcher(), max_per_unit=10)
    assert result == {
        "宿": [Match("宿", "しゅく", w("宿泊[しゅくはく]"))],
        "題": [Match("題", "だい", w("問題[もんだい]")), Match("題", "だい", w("話題[わだい]"))],
    }
    assert len(find_matches(target, index, DumbMatcher(), max_per_unit=1)["題"]) == 1


def test_make_matcher() -> None:
    assert isinstance(make_matcher("dumb", 2, True), DumbMatcher)
    try:
        make_matcher("nope", 2, True)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def run(a: str, b: str) -> Optional[tuple[str, str]]:
    return DumbMatcher().shared_run(w(a), w(b))


def test_no_spill_into_shared_neighbour() -> None:
    # 問題 / 問題集 share 題 after 問 too, so 問 alone can't be labelled from this pair.
    assert shared("問題[もんだい]", "問題集[もんだいしゅう]", "問") is None
    assert shared("学生[がくせい]", "大学生[だいがくせい]", "生") is None
    assert shared("大学生[だいがくせい]", "大学院生[だいがくいんせい]", "生") == "せい"  # neighbours differ


def test_shared_run() -> None:
    cases = [
        ("問題[もんだい]", "問題集[もんだいしゅう]", ("問題", "もんだい")),  # candidate contains target
        ("問題集[もんだいしゅう]", "問題[もんだい]", ("問題", "もんだい")),  # target contains candidate
        ("学生[がくせい]", "大学生[だいがくせい]", ("学生", "がくせい")),  # shared at the end
        ("日本人[にほんじん]", "日本語[にほんご]", ("日本", "にほん")),  # partial run
        ("時計[とけい]", "腕時計[うでどけい]", ("時計", "とけい")),  # rendaku at the inner edge
        ("問題[もんだい]", "大問題集[だいもんだいしゅう]", ("問題", "もんだい")),  # in the middle
    ]
    for a, b, expected in cases:
        assert run(a, b) == expected, (a, b)


def test_shared_run_different_reading() -> None:
    assert run("一日[ついたち]", "一日中[いちにちじゅう]") is None
    assert run("宿題[しゅくだい]", "問題[もんだい]") is None  # only one kanji in common


def test_find_matches_runs_and_consensus() -> None:
    target = w("問題[もんだい]")
    fields = ["学問[がくもん]", "質問[しつもん]", "疑問[ぎもん]", "問題集[もんだいしゅう]", "話題[わだい]"]
    result = find_matches(target, KanjiIndex(map(w, fields)), DumbMatcher(), max_per_unit=10)
    assert result == {
        "問": [Match("問", "もん", w(f)) for f in ("学問[がくもん]", "質問[しつもん]", "疑問[ぎもん]")],
        "題": [Match("題", "だい", w("話題[わだい]"))],
        "問題": [Match("問題", "もんだい", w("問題集[もんだいしゅう]"))],
    }


def test_consensus_relabels_spilled_reading() -> None:
    # 学説 alone gives がくせ (せい/せつ share せ); 学校 and 大学 agree on がく.
    target = w("学生[がくせい]")
    fields = ["学校[がっこう]", "大学[だいがく]", "学説[がくせつ]"]
    result = find_matches(target, KanjiIndex(map(w, fields)), DumbMatcher(), max_per_unit=10)
    assert [(m.word.surface, m.reading) for m in result["学"]] == [("学校", "がく"), ("大学", "がく"), ("学説", "がく")]


def test_consensus_keeps_majority_over_short_outlier() -> None:
    matches = [Match("間", "かん", w(f)) for f in ("期間[きかん]", "空間[くうかん]")] + [
        Match("間", "ん", w("人間[にんげん]"))
    ]
    assert [m.reading for m in settle_readings(matches)] == ["かん", "かん", "ん"]
