## Mioboeru (見覚える)

Finds other notes in your collection whose words share a kanji **with the same reading**
as the target word, and writes them to a field. Example: 宿題 -> 問題 (題 = だい in both).

* `note_types` - exact names of the note types mioboeru fills and searches. Must not be empty.
* `target_decks` - decks (subdecks included) whose notes "Fill related words (target decks)"
  fills. Must not be empty for that action. Notes selected in the browser and the editor button
  ignore this, since you picked those notes yourself. Matches still come from all decks.
* `reading_field` - field holding the word with its reading as furigana (e.g. `宿題[しゅくだい]`).
  Used both for the target word and for every word searched in the collection.
* `destination_field` - field that receives the matched words: one line per kanji of the
  target word, with the shared kanji in bold, e.g. for 難題:
  `なん：非<b>難</b>、無<b>難</b>、<b>難</b>解` and `だい：話<b>題</b>、問<b>題</b>`.
* `line_prefix_template` - text at the start of each line. `{reading}` is replaced with the
  kanji's reading in the target word (hiragana), `{kanji}` with the kanji itself.
  Default `{reading}：`. If a kanji's matches share different readings, each gets its own line.
* `word_template` - how each matched word is written. `{word}` is the word with the shared kanji
  in bold, `{reading}` is the word's full reading. Default `{word}`. Examples:
  `{word}({reading})` -> `部<b>分</b>(ぶぶん)`, `<ruby>{word}<rt>{reading}</rt></ruby>` for ruby furigana.
* `search_query` - extra Anki search that narrows which notes of `note_types` can be listed as
  matches (e.g. `-is:new`, `deck:Japanese`). It doesn't change which notes get filled.
  Empty means no extra filter.
* `match_method` - how to decide that a kanji is read the same way in two words.
  * `dumb` - uses whole-word readings only. Matches when the kanji is the first or last kanji
    in both words and the readings start/end the same (宿題 <-> 問題 on だい).
    Kanji in the middle of 3+ kanji words are skipped.
    When the words share 2+ characters together (問題 in 問題集, 日本 in 日本語), the reading of
    each kanji can't be told apart, so the shared part gets its own line: `もんだい：<b>問題</b>集`.
    If one word suggests a longer reading than most others (学説 -> がくせ), the reading most
    matches agree on is shown instead (がく).
* `min_shared_kana` - shortest shared reading (in kana) accepted by `dumb`. Lower values find
  more one-kana readings (天気 <-> 元気 on き) but also more false matches (時間 <-> 人間 on ん).
  A single-kanji word (気[き]) always counts as its kanji's full reading.
* `fuzzy_kana` - treat sound changes where kanji meet as the same reading:
  voicing (き/ぎ, ほ/ぼ/ぽ) and gemination (つ/く/ち/き -> っ, e.g. 学 がく <-> 学校 がっこう).
* `max_matches` - maximum number of words listed per kanji.
* `overwrite_destination` - if `false`, bulk runs skip notes whose destination field is non-empty.
  The editor button always overwrites.

Run it from:
* **AJT > Mioboeru > Fill related words (target decks)**
* the browser: **Edit > Mioboeru: Fill related words (selected notes)**
* the editor (Add, Browse and Edit windows): the **読** toolbar button fills the current note.

All of these can be undone with Edit > Undo.
