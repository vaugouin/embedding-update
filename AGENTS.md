# AGENTS.md - Agent Guide for Embedding Update

This file gives you the agentic context you need to work on this codebase safely. For project overview, features, install / deploy steps and human-facing security / performance / troubleshooting material, read @README.md — that file is canonical and not duplicated here.

This is the single canonical guide for autonomous coding agents in this repository. Assistant-specific files such as @CLAUDE.md, and any future tool-specific guide such as `GEMINI.md`, should only point here and should not duplicate repository instructions.

Deeper specs live in their own files:
- @doc/sql/*.sql — reference DDL for the database schema; treat these files as read-only unless the user explicitly asks you to edit schema documentation

- For any project update, keep documentation aligned:
  - Update `README.md` for user-facing behavior, configuration, setup, deployment, troubleshooting, or verification changes.
  - Update this file only when agent workflow or safety context changes.

---

## Related repositories (project ecosystem)

`embedding-update` is one stage of **Agent BBB**, a multi-repository movie/TV database system owned by GitHub user `vaugouin`. All sibling repos live under `%USERPROFILE%/Code/<repo>` and at `github.com/vaugouin/<repo>`; they are interdependent stages of one pipeline that converges on a shared MySQL/MariaDB database (`T_WC_*` tables) and a ChromaDB vector store. The canonical roster of sibling repositories is kept in `%USERPROFILE%/Nestor/projets/t2s-backlog/topics/related-repositories.txt` (documentation repo `Nestor`, outside `Code/`).

Pipeline stages:
- **Infrastructure** — `python` (shared crawler base image), `chromadb` (vector service), `reverseproxy` (NGINX TLS ingress), `chromadb-security-test` (firewall validation), `tools` (host-side operational scripts for the shared MariaDB: backups per perimeter, one-off `.sql` runs; **private repo**, it documents where the database lives and how it is restored).
- **Acquisition** — `tmdb-crawler`, `imdb-crawler`, `sparql-crawler`, `sparql-movies-persons`, `wikidata-crawler`, `wikipedia-crawler`, `selenium-tmdb`, `download-images`, `sqlite-plex-to-tmdb`, `movieparadise`.
- **Preprocessing → `T_WC_T2S_*`** — `tmdb-movie-preprocess`, `tmdb-person-preprocess`, `keywords-processing`.
- **Semantic index & name resolution** — `embedding-update`, `embedding-query`, `rapidfuzz_query`.
- **Serving** — `fastapi-text2sql` (NL→SQL API + MCP server), `voice-agent`, `tmdb-front` (PHP web front-end).
- **Evaluation** — `eval-text2sql`, `extract-movie-questions`.
- **Maintenance & tooling** — `plex-duplicates`, `subtitle-translate`, `powershell`, `playwright-test`.
- **Monitoring & observability** — `data-monitoring`.

**This repository's role:** Semantic-index stage. Keeps the ChromaDB vector collections (served by the `chromadb` repo) in sync with the `T_WC_T2S_*` read-model produced by the preprocessing repos. The collections it maintains are consumed by `fastapi-text2sql` for entity resolution and cache lookup, and exercised by `embedding-query`.

---

## Where things live (file → role)

Edit at the right layer; the architecture is intentionally split.

## Code conventions

- **Hungarian notation** for variables (legacy style):
  - `str` — strings (`strtablename`, `strapiversion`)
  - `lng` — integers (`lngpage`, `lngrowsperpage`)
  - `dbl` — floats (`dblavailableram`)
  - `arr` — lists / arrays
  - `int` — boolean-like flags (`intcleanupenabled`, `intentity`)
- **Function naming**: public pipeline entry points use `f_` (`f_text2sql`, `f_entity_extraction`, `f_resolve_complex_question`, `f_answer_single_value`, `f_hello_world`); private helpers use `_` (`_call_chat_llm`, `_normalize_llm_model`).
- **Docstrings**: Google-style on public functions.
- **Error handling**: broad try/except with console logging; surface failures via the `error` response field and the `messages` trace. Database execution errors are not returned directly to clients — they go through the complex-question retry path when enabled.
- **JSON serialization**: use `logs.decimal_serializer()` for `Decimal` and `datetime`.

---

## Database Schema Sources

Full DDL lives under [doc/sql/](doc/sql/); do not duplicate table definitions here. Treat these files as reference-only unless the user explicitly asks for schema-doc edits.

- [doc/sql/T2S-tables.sql](doc/sql/T2S-tables.sql) — canonical Text2SQL read-model tables used for embeddings update.

---

## SQL Object Naming Conventions

- SQL table and column names are uppercase snake case, except legacy imported TMDb genre columns such as `id` and `name`.
- Persistent tables use `T_WC_*`.
- Text2SQL read-model tables use `T_WC_T2S_*`.
- TMDb source/reference tables use `T_WC_TMDB_*`.
- Wikidata tables use `T_WC_WIKIDATA_*`; staging tables use `STG_T_WC_WIKIDATA_*`.
- Wikipedia tables use `T_WC_WIKIPEDIA_*`.
- Join tables usually follow `T_WC_T2S_{PARENT}_{CHILD}`, for example `T_WC_T2S_MOVIE_GENRE`, `T_WC_T2S_PERSON_MOVIE`.
- Primary keys are usually `ID_{ENTITY}` for entity tables, `ID_ROW` for generic/join rows, or a table-specific surrogate such as `ID_T2S_PERSON_MOVIE`.
- Foreign keys reuse the referenced primary-key name, for example `ID_MOVIE`, `ID_PERSON`, `ID_GENRE`.
- Date columns use `DAT_*`; datetime/timestamp columns use `TIM_*`.
- Boolean-like flags use `IS_*` or legacy integer flags such as `DELETED`.
- Ordering uses `DISPLAY_ORDER`.
- Aggregate counters use `*_COUNT`.
- Media paths use `*_PATH`.
- Language-specific labels/titles often use suffixes such as `_FR`; generic language rows use `LANG`.
- RapidFuzz/generated search columns use `*_NORM` and `*_KEY`; popularity tie-breakers commonly use `POPULARITY`.
- Index names are mixed legacy style. Preserve existing style: simple `KEY COLUMN_NAME`, `IDX_*` for indexes, `UK_*` for unique keys, `FK_*` for foreign keys, and `ft_*` for FULLTEXT indexes.

---

## Encoding

Keep Markdown, prompt files, JSON config, and logs UTF-8. These files contain non-ASCII names and multilingual examples. Avoid editor or terminal operations that rewrite them with mojibake.

---

## Incremental passes: the two watermarks that decide what gets re-indexed

Every pass is incremental, and what it processes is decided by **two** server variables per
entity, not one. Both live in `<DB_NAMESPACE>SERVER_VARIABLE` (`VAR_NAME`, `VAR_VALUE`,
`DELETED = 0`) and are named from `strservervariableprefix = "strembeddingupdate"`:

| Variable | Role |
|---|---|
| `strembeddingupdate<entity>startdatetime` | date watermark: only rows with `TIM_UPDATED >=` this value are read |
| `strembeddingupdate<entity>id` | **resume marker**: when non-empty, only rows with `<key> >=` this value are read |

`<entity>` is the singular `strentityname`, so the list pass reads
`strembeddingupdateliststartdatetime` and `strembeddingupdatelistid`.

The three processing functions (`f_process_bilingual_t2s_entity_embeddings`,
`f_process_en_fr_original_title_embeddings_from_lang_table`,
`f_process_single_language_entity_embeddings`) all build the same filter, and they **combine**:

```sql
-- when the id watermark is non-empty
WHERE <key> >= <id>  AND TIM_UPDATED >= '<startdatetime>'
-- when it is empty
WHERE TIM_UPDATED >= '<startdatetime>'
```

`locations` is the exception in form only: it is processed inline with hand-written SQL rather
than through one of the three functions, but it applies the same two filters
(`strlocationidold` and `strlocationstartdatetimeprevious`), so the rules below still hold.

**Lifecycle, and this is the part that is easy to get wrong.** The id variable is rewritten on
**every row** as the loop advances, so an interrupted pass leaves it pointing at the last entity
processed and the next pass resumes from there. At the end of a clean pass it is reset to the
empty string and the date variable is set to **that pass's start time**, not its end, so rows
modified while the pass was running are still caught by the next one.

Consequence: **after any clean pass the id watermark is empty and only the date filter applies.**
It is non-empty only when the previous pass died mid-way.

### Forcing a re-index of specific rows

Changing what gets *indexed* (the document text) does not re-index anything by itself: the rows
must look modified. Touch them, then check the resume marker is not standing in the way.

```sql
-- 1. read both watermarks first
SELECT VAR_NAME, VAR_VALUE
FROM   T_WC_SERVER_VARIABLE
WHERE  DELETED = 0
AND    VAR_NAME IN ('strembeddingupdate<entity>startdatetime',
                    'strembeddingupdate<entity>id');

-- 2. make the rows eligible
UPDATE <table> SET TIM_UPDATED = NOW() WHERE <your condition>;

-- 3. ONLY if step 1 returned a non-empty id ABOVE the ids you just touched,
--    clear it, or the pass will skip them despite the fresh date
UPDATE T_WC_SERVER_VARIABLE SET VAR_VALUE = '0'
WHERE  DELETED = 0 AND VAR_NAME = 'strembeddingupdate<entity>id';
```

`'0'` rather than `''` is deliberate: the code tests `if stroldid != ""`, so an empty string
drops the id clause entirely while `'0'` yields `>= 0`, which excludes nothing. Either works.

Re-indexing replaces cleanly: the functions `delete(ids=[strdocid])` before `add(...)`, so no
stale document survives with the old text.

**Worked example, 2026-08-29.** The list pass stopped appending `OVERVIEW` to the indexed
document (`overview_field=None`, mirroring `groups`). Four rows carried an overview, so four
rows needed `TIM_UPDATED` touched; nothing else in the table had a document change.

## `t2slocations` (process 216): what an agent must not undo

The collection of the locations read-model, EMBEDDING-UPDATE-005. The README carries the user-facing
description; these are the constraints.

- **Created here, explicitly configured, and nowhere else.** `f_getorcreatet2slocationscollection()`
  passes `T2SLOCATIONS_HNSW_CONFIGURATION` (`space l2`, `ef_search 100`, `ef_construction 100`,
  `max_neighbors 16`). Chroma ignores the configuration on an existing collection and `space` can
  never be changed, so the first program to call `get_or_create_collection("t2slocations")` wins for
  ever. Consumers (`fastapi-text2sql`, `embedding-query`) must use `get_collection`. The function reads
  the configuration back and prints it at every start; it never raises, because a failure on this one
  collection must not stop the fifteen others (`t2slocations` is then `None` and 216 skips the run).
- **Keyed on `ID_LOCATION`, which requires the process 72 fix of 2026-09-13.** Before it,
  `tmdb-movie-preprocess` renumbered `ID_LOCATION` at every nightly rebuild (the INSERT of step 1c
  listed no `ID_LOCATION`); since the fix the id is carried over by a join on the served table, places
  that left the perimeter stay as `DELETED = 1` rows, new ids go above the served maximum. Document id
  `t2slocationid_<ID_LOCATION>_<lang>`, `id_wikidata` in the metadata like deaths and nominations.
  Never build this collection against a preprocess that predates the fix: every night would re-key
  and re-embed the whole collection.
- **The French document is skipped on the label, not on the document.** The type word is translated,
  so two documents of a place with the same label in both languages never compare equal; the rule of
  the other collections (skip FR when identical to EN) is therefore applied to `LOCATION_NAME_FR ==
  LOCATION_NAME`. `deduplicate-embeddings.py` would find nothing to do on this collection.
- **No silent full-scan fallback.** Process 209 replays its query without the date filter on any
  exception; 216 lets the error surface. Watermarks and their reset follow the two-variable lifecycle
  above (`strembeddingupdatet2slocationstartdatetime`, `strembeddingupdatet2slocationid`).
- **216 is the last process of the scope**, so the end-of-run marker is `if intindex == 216`. A process
  added after it must move that marker, or `currentcontent` is cleared one process too early and a
  crash in the new process would not resume. Being last also means `UPDATE T_WC_SERVER_VARIABLE SET
  VAR_VALUE = 't2slocation' WHERE VAR_NAME = 'strembeddingupdatecurrentcontent'` runs 216 alone, which
  is the way to run it on demand without editing code.
- **`chromadb` is pinned to the 1.x line** (`>=1.0.0,<2.0.0`) because the `configuration=` parameter
  belongs to the 1.x client; the code still falls back to the legacy `hnsw:*` metadata keys if the
  parameter is missing.

## Build & deployment (Docker)

The embeddings-update job is built and run as a Docker container via the repo's `Dockerfile` (base image `python:3.10.5-slim-bullseye`). The build adds toolchain deps and compiles SQLite 3.40.1 from source (set on `LD_LIBRARY_PATH`) for ChromaDB compatibility, installs `requirements.txt`, copies the repo, and runs `CMD ["python", "./embedding-update.py"]`. No ports or volumes are exposed; DB and ChromaDB targets come from runtime configuration.

**Convention — everything that runs on the VPS runs under Docker.** Any program in
this ecosystem that executes on the VPS (the main job, one-off maintenance scripts,
backfills) runs inside a container, never as a bare `python script.py` on the host.
Don't bake secrets into the image: pass them at runtime with
`--env-file /home/debian/docker/<repo>/.env`. Use `--network host` so the container
reaches host-local services (ChromaDB on `127.0.0.1:8100`, MariaDB).

**Running a one-off script (e.g. a backfill) reuses this image** by overriding the
`CMD` after the image name — no separate Dockerfile needed. Example, the movie-year
metadata backfill (`backfill-movie-year.py`):

```bash
cd /home/debian/docker/embedding-update
docker build -t embedding-update-python-app .
# dry-run first (reports only, writes nothing):
docker run -it --rm --network host \
  --env-file /home/debian/docker/embedding-update/.env \
  --name embedding-update-backfill \
  embedding-update-python-app python backfill-movie-year.py --dry-run
# then the real run:
docker run -it --rm --network host \
  --env-file /home/debian/docker/embedding-update/.env \
  --name embedding-update-backfill \
  embedding-update-python-app python backfill-movie-year.py
```

Use a distinct `--name` (not `embedding-update`) so a one-off never collides with
the scheduled job's container, and `-it` (foreground) to watch progress.

---

**Last Updated**: 2026-06-24
**Current Version**: 1.0.0 

## Backlog (Nestor second-brain)

The prioritized, agent-ready implementation backlog for this repo lives in the **Nestor**
knowledge repo (a separate repo, not cloned alongside this one):

- This repo: `C:\Users\vaugo\Nestor\projets\t2s-backlog\repos\embedding-update.md`
- Cross-repo dashboard: `C:\Users\vaugo\Nestor\projets\t2s-backlog\index.md`

Consult it before implementing: tasks are `EMBEDDING-UPDATE-NNN` with status (done / in-progress /
todo), priority, and quick-wins. NOTE: these are local paths on Philippe's PC and do not
resolve on the VPS or on cloud agents (claude.ai/code).
