# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from collections.abc import Sequence

from .ajt_common.addon_config import AddonConfigManager


class MioboeruConfig(AddonConfigManager):
    @property
    def note_types(self) -> Sequence[str]:
        return self["note_types"]

    @property
    def target_decks(self) -> Sequence[str]:
        return self["target_decks"]

    @property
    def reading_field(self) -> str:
        return self["reading_field"]

    @property
    def destination_field(self) -> str:
        return self["destination_field"]

    @property
    def line_prefix_template(self) -> str:
        return self["line_prefix_template"]

    @property
    def word_template(self) -> str:
        return self["word_template"]

    @property
    def search_query(self) -> str:
        return self["search_query"]

    @property
    def max_matches(self) -> int:
        return self["max_matches"]

    @property
    def overwrite_destination(self) -> bool:
        return self["overwrite_destination"]

    @property
    def match_method(self) -> str:
        return self["match_method"]

    @property
    def min_shared_kana(self) -> int:
        return self["min_shared_kana"]

    @property
    def fuzzy_kana(self) -> bool:
        return self["fuzzy_kana"]
