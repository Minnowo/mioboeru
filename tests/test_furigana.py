# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from mioboeru.furigana import Word, parse_furigana


def test_parse_furigana() -> None:
    cases = {
        "異様[いよう]": Word("異様", "いよう"),
        " 異様[いよう]": Word("異様", "いよう"),
        "<b>宿題[しゅくだい]</b>": Word("宿題", "しゅくだい"),
        "一人暮[ひとりぐ]らし": Word("一人暮らし", "ひとりぐらし"),
        "お 茶[ちゃ]": Word("お茶", "おちゃ"),
        "ビール": Word("ビール", "びーる"),
        "異様[イヨウ]": Word("異様", "いよう"),
    }
    for field, expected in cases.items():
        assert parse_furigana(field) == expected, field


def test_parse_furigana_rejects_unusable() -> None:
    for field in ("", "  ", "異様", "<br>"):
        assert parse_furigana(field) is None, field
