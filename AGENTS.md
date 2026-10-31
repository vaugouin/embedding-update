# AGENTS.md - Agent Guide for Embedding Update

Canonical agent guide for this repo (`CLAUDE.md` and any other tool-specific file only point here). Overview, collections, document-id patterns, process table, install and run steps are in @README.md; reference DDL is in @doc/sql/ (read-only unless asked). Update `README.md` for user-facing changes, this file only when agent workflow or safety context changes.

---

## Related repositories (project ecosystem)

Semantic-index stage of **Agent BBB** (`github.com/vaugouin/<repo>`, cloned under `%USERPROFILE%/Code/<repo>`): keeps the ChromaDB collections (served by `chromadb`) in sync with the `T_WC_T2S_*` read-model built by the preprocessing repos; `fastapi-text2sql` reads them for entity resolution and cache lookup, `embedding-query` exercises them. Roster: `%USERPROFILE%/Nestor/projets/t2s-backlog/topics/related-repositories.txt`; stage map: `tmdb-front/AGENTS.md` § Related repositories.

---

## Code conventions

- **Hungarian notation** for variables (legacy style): `str` strings, `lng` integers, `dbl` floats, `arr` lists, `int` boolean-like flags. Functions use the `f_` prefix.
- SQL names follow the `T_WC_*` conventions visible in `doc/sql/` (uppercase snake case, `T_WC_T2S_*` read-model, `ID_*` keys, `TIM_*` timestamps, `DELETED` flag); preserve the existing legacy style of index names.
- Keep Markdown, prompts, JSON and logs UTF-8 (non-ASCII names); avoid tools that rewrite them with mojibake.

---

## Incremental passes: the two watermarks that decide what gets re-indexed

Each entity pass is filtered by **two** server variables in `T_WC_SERVER_VARIABLE` (prefix `strembeddingupdate` + singular entity name, e.g. `strembeddingupdatelist...`):

| Variable | Role |
|---|---|
| `strembeddingupdate<entity>startdatetime` | date watermark: rows with `TIM_UPDATED >=` this value |
| `strembeddingupdate<entity>id` | **resume marker**: when non-empty, also `<key> >=` this value |

The three generic `f_process_*_embeddings` functions combine both filters (`WHERE <key> >= <id> AND TIM_UPDATED >= '<start>'`); `f_process_t2slocation_embeddings` (216/217) follows the same two-variable lifecycle.

**Lifecycle, easy to get wrong.** The id variable is rewritten on every row, so an interrupted pass resumes from the last entity. A clean pass resets it to `''` and sets the date variable to **that pass's start time** (not its end), so rows modified during the pass are caught next time. After a clean pass the id marker is empty; it is non-empty only when the previous pass died.

### Forcing a re-index of specific rows

Changing the document text re-indexes nothing by itself: the rows must look modified, and the resume marker must not stand in the way.

```sql
-- 1. read both watermarks
SELECT VAR_NAME, VAR_VALUE FROM T_WC_SERVER_VARIABLE
WHERE  DELETED = 0
AND    VAR_NAME IN ('strembeddingupdate<entity>startdatetime', 'strembeddingupdate<entity>id');
-- 2. make the rows eligible
UPDATE <table> SET TIM_UPDATED = NOW() WHERE <your condition>;
-- 3. ONLY if step 1 returned a non-empty id ABOVE the touched ids, clear it
UPDATE T_WC_SERVER_VARIABLE SET VAR_VALUE = '0'
WHERE  DELETED = 0 AND VAR_NAME = 'strembeddingupdate<entity>id';
```

`'0'` and `''` both work (the code tests `stroldid != ""`; `'0'` yields `>= 0`). Re-indexing replaces cleanly (`delete` before `add`).

## `t2slocations` (process 216): what an agent must not undo

User-facing description: README § Process 216. Constraints:

- **Created only here, with `T2SLOCATIONS_HNSW_CONFIGURATION`.** Chroma ignores the configuration on an existing collection and `space` can never change, so the first `get_or_create_collection("t2slocations")` wins for ever: consumers (`fastapi-text2sql`, `embedding-query`) must use `get_collection`. `f_getorcreatet2slocationscollection()` never raises (a failure skips 216, not the other collections).
- **Keyed on `ID_LOCATION`, which needs the process 72 fix of `tmdb-movie-preprocess` (2026-09-13)** that keeps ids stable across the nightly rebuild. Never build it against a preprocess predating the fix: every night would re-key and re-embed everything.
- **French document skipped on the label** (`LOCATION_NAME_FR == LOCATION_NAME`), not on the document, because the type word is translated. `deduplicate-embeddings.py` therefore finds nothing on this collection.
- **No silent full-scan fallback** (unlike retired process 209): errors surface.
- **217 (`t2ssourceworks`, EMBEDDING-UPDATE-011) is the last process since 2026-10-10**: the end-of-run marker is `if intindex == 217`; 216 and 217 share `f_process_t2slocation_embeddings` (column names are parameters). A process added after it must move that marker, or `currentcontent` is cleared one process early and a crash in the new process would not resume. Setting `strembeddingupdatecurrentcontent` to `t2slocation` starts a run at 216 (followed by 217), without editing code.
- **No counters in the metadata** (EMBEDDING-UPDATE-013, 2026-10-19): `MOVIE_COUNT`/`SERIE_COUNT`/`EPISODE_COUNT` stay out, since no resolver reads metadata and they change nightly. Revisit with FASTAPI-TEXT2SQL-258.
- **Coverage check:** `check-t2slocations-coverage.py` (read-only; run on the VPS in the job image, command in its docstring; ChromaDB is not reachable from SQL or the PC).
- **`chromadb` pinned to 1.x** (`requirements.txt`) because `configuration=` belongs to the 1.x client; the code falls back to legacy `hnsw:*` keys.

## Build & deployment (Docker)

**Everything that runs on the VPS runs under Docker**, including one-off maintenance scripts and backfills, never a bare `python script.py` on the host. Secrets only at runtime (`--env-file /home/debian/docker/<repo>/.env`), never baked into the image; `--network host` to reach ChromaDB (`127.0.0.1:8100`) and MariaDB. A one-off reuses the job image by overriding `CMD`, with a distinct `--name` so it never collides with the scheduled `embedding-update` container: see README § Running with Docker.

---

**Last Updated**: 2026-10-31
**Current Version**: 1.0.5 

## Backlog (Nestor second-brain)

Backlog (`EMBEDDING-UPDATE-NNN`, status and priority) in the Nestor repo: `C:\Users\vaugo\Nestor\projets\t2s-backlog\repos\embedding-update.md` (dashboard: `...\t2s-backlog\index.md`). Consult it before implementing. Local paths on Philippe's PC only; they do not resolve on the VPS or cloud agents.
