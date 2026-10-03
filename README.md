# Mioboeru (見覚える)

Anki add-on that links vocabulary notes sharing a kanji **with the same reading**.
For a note with 宿題, it finds e.g. 問題 (題 = だい) and writes it to a field on the note.

Targets Anki 25.02.7 (Python 3.9). Built on [ajt_common](https://github.com/Ajatt-Tools/ajt_common).

## Development

```bash
git submodule update --init      # fetch mioboeru/ajt_common
./scripts/fetch_anki_docs.sh     # optional: offline Anki add-on docs
hatch run dev:test
./scripts/package.sh             # -> ajt_mioboeru.ankiaddon
```
