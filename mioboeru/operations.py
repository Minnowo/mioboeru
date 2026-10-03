# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Collection-side work: index the collection and write matches into notes."""

from collections.abc import Sequence
from typing import Optional

from anki.collection import Collection, OpChanges, OpChangesWithCount, SearchNode
from anki.models import NotetypeId
from anki.notes import Note, NoteId
from anki.utils import ids2str

from .config import MioboeruConfig
from .formatting import format_matches
from .furigana import parse_furigana
from .matching import KanjiIndex, find_matches, make_matcher

ADDON_NAME = "Mioboeru"
FIELD_SEPARATOR = "\x1f"


def _any_of(col: Collection, nodes: Sequence[SearchNode]) -> str:
    return col.build_search_string(*nodes, joiner="OR")


def _note_types_search(col: Collection, config: MioboeruConfig) -> str:
    if not config.note_types:
        raise ValueError("No note types configured. Choose them in AJT > Mioboeru > Options.")

    return _any_of(col, [SearchNode(note=name) for name in config.note_types])


def source_search(col: Collection, config: MioboeruConfig) -> str:
    """Notes whose words can be listed as matches: configured note types, narrowed by `search_query`."""
    search = _note_types_search(col, config)

    if config.search_query:
        search = col.build_search_string(search, config.search_query)

    return search


def target_search(col: Collection, config: MioboeruConfig) -> str:
    """Notes filled by a bulk run: configured note types in the target decks (and their subdecks)."""
    if not config.target_decks:
        raise ValueError("No target decks configured. Choose them in AJT > Mioboeru > Options.")

    return col.build_search_string(
        _note_types_search(col, config),
        _any_of(col, [SearchNode(deck=name) for name in config.target_decks]),
    )


def build_index(col: Collection, config: MioboeruConfig) -> KanjiIndex:
    # Read fields straight from the notes table: much faster than col.get_note() on big collections.
    nids = col.find_notes(source_search(col, config))

    field_ords: dict[NotetypeId, Optional[int]] = {}
    index = KanjiIndex()

    for mid, flds in col.db.execute(f"select mid, flds from notes where id in {ids2str(nids)}"):
        if mid not in field_ords:
            note_type = col.models.get(mid)
            entry = col.models.field_map(note_type).get(config.reading_field) if note_type else None
            field_ords[mid] = entry[0] if entry else None

        if (ord_ := field_ords[mid]) is not None and (word := parse_furigana(flds.split(FIELD_SEPARATOR)[ord_])):
            index.add(word)

    return index


def can_fill(note: Note, config: MioboeruConfig) -> bool:
    note_type = note.note_type()

    return (
        note_type is not None
        and note_type["name"] in config.note_types
        and config.reading_field in note
        and config.destination_field in note
    )


def related_words(note: Note, index: KanjiIndex, config: MioboeruConfig) -> Optional[str]:
    """New destination field value for the note, or None if its reading field can't be parsed."""
    word = parse_furigana(note[config.reading_field])

    if word is None:
        return None

    matcher = make_matcher(config.match_method, config.min_shared_kana, config.fuzzy_kana)

    return format_matches(
        find_matches(word, index, matcher, config.max_matches),
        config.line_prefix_template,
        config.word_template,
    )


def fill_related_op(col: Collection, nids: Sequence[NoteId], config: MioboeruConfig) -> OpChangesWithCount:
    """Fill the destination field of the given notes. Returns the number of notes changed."""
    make_matcher(config.match_method, config.min_shared_kana, config.fuzzy_kana)  # fail early on bad config

    index = build_index(col, config)
    to_update = []

    for nid in nids:
        note = col.get_note(nid)

        if not can_fill(note, config):
            continue

        if not config.overwrite_destination and note[config.destination_field].strip():
            continue

        new_value = related_words(note, index, config)

        if new_value is not None and note[config.destination_field] != new_value:
            note[config.destination_field] = new_value
            to_update.append(note)

    if not to_update:
        return OpChangesWithCount(count=0)  # don't leave an empty step in the undo history

    pos = col.add_custom_undo_entry(f"{ADDON_NAME}: fill related words in {len(to_update)} notes")
    col.update_notes(to_update)

    return OpChangesWithCount(count=len(to_update), changes=col.merge_undo_entries(pos))


def fill_note_op(col: Collection, note: Note, config: MioboeruConfig) -> OpChanges:
    """Fill (always overwriting) one note open in an editor. It may not be in the collection yet."""
    if not can_fill(note, config):
        raise ValueError(
            f"This note type isn't configured for {ADDON_NAME}, or it lacks the "
            f"'{config.reading_field}' / '{config.destination_field}' fields."
        )

    new_value = related_words(note, build_index(col, config), config)

    if new_value is None:
        raise ValueError(f"Couldn't read a word with furigana from '{config.reading_field}', e.g. 宿題[しゅくだい].")

    note[config.destination_field] = new_value

    if note.id == 0:
        return OpChanges()  # Add window: the note is saved when the user adds it

    pos = col.add_custom_undo_entry(f"{ADDON_NAME}: fill related words")
    col.update_note(note)

    return col.merge_undo_entries(pos)
