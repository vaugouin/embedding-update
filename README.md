# Embedding Update

This repository contains a Python script, `embedding-update.py`, used to maintain vector embeddings in a ChromaDB instance from data stored in a MySQL database. It focuses on media-related entities such as topics, movies, series, and persons, and keeps their embeddings in sync with the source tables.

## Overview

`embedding-update.py`:

- **Loads configuration** from environment variables using `python-dotenv`.
- **Uses OpenAI embeddings** (`text-embedding-3-large`) via the OpenAI API.
- **Connects to ChromaDB** (HTTP client on `localhost:8100`) with a custom embedding function.
- **Connects to a MySQL database** via helper functions defined in the local `citizenphil` module.
- **Creates/loads ChromaDB collections**:
  - `topics`
  - `movies`
  - `series`
  - `persons`
  - `companies`
  - `networks`
  - `characters` (collection exists but processing is currently disabled — see Processes)
  - `groups`
  - `locations`
  - `anonymizedqueries`
  - `awards`
  - `nominations` (bilingual EN/FR; overview appended to text)
  - `lists`
  - `collections`
  - `deaths` (bilingual EN/FR; overview appended to text)
  - `movements`
- **Iterates over entities** in the database and for each entity type:
  - Builds a stable document ID like `topicid_<ID>_<LANG>` or `movieid_<ID>_<LANG>`.
  - Creates or updates the corresponding document in ChromaDB.
  - Deletes documents whose source rows have been deleted or no longer meet criteria.
- **Persists progress and runtime metadata** via `citizenphil.f_setservervariable` so the process can resume from the last processed IDs.

The script is designed to be run periodically (e.g. by a scheduler or cron-like system) to keep the vector store synchronized with the relational database.

## Requirements

- Python 3.9+ (recommended)
- Access to:
  - An OpenAI API key
  - A running ChromaDB HTTP server (default: `localhost:8100`)
  - A MySQL-compatible database with the required tables
- The following Python packages (see `embedding-update.py` imports):
  - `pandas`
  - `numpy`
  - `openai`
  - `python-dotenv`
  - `chromadb`
  - `psutil`
  - `pymysql`
  - Local module: `citizenphil` (project-specific, not provided on PyPI)

Install the dependencies, for example:

```bash
pip install pandas numpy openai python-dotenv chromadb psutil pymysql
```

You also need the `citizenphil` module available on the Python path (typically part of the same codebase or installed as a private package).

## Configuration

### Environment variables

The script expects an `.env` file (or equivalent environment variables) providing at least:

- `OPENAI_API_KEY` – your OpenAI API key

`python-dotenv` loads this automatically at startup.

### Claude (Anthropic) support

This project can be configured to use Anthropic/Claude as an alternative embedding provider. See `CLAUDE.md` for setup instructions, environment variables, and a minimal usage example. If you choose Claude, set `CLAUDE_API_KEY` (or add it to `citizenphilsecrets.py`) and update the embedding wrapper in `embedding-update.py` to call the Claude SDK instead of OpenAI.

### ChromaDB

The script connects to ChromaDB via:

- Host: `localhost`
- Port: `8100`

Make sure a ChromaDB HTTP server is running and accessible at this address before starting the script.

### Database and `citizenphil`

Database access, timezone (`paris_tz`), and server-variable storage are handled by the `citizenphil` module via objects/functions like:

- `cp.connectioncp`
- `cp.f_getservervariable`
- `cp.f_setservervariable`
- `cp.paris_tz`

These are project-specific and must be configured in `citizenphil` (not in this file).

## How `embedding-update.py` works

At a high level, the script:

1. **Initializes services**
   - Loads `.env` and validates `OPENAI_API_KEY`.
   - Instantiates `OpenAIEmbeddingFunction` (wrapper around `openai.embeddings.create`).
   - Creates a `chromadb.HttpClient` and collections for each entity type.
   - Logs memory usage via `psutil`.

2. **Loads previous state** from `cp.f_getservervariable`, such as:
   - Last processed IDs per entity type
   - Currently processed entity kind (`strembeddingupdatecurrentcontent`)
   - Execution metadata and reports

3. **Processes each entity type** (topics, movies, series, persons, companies, networks, groups, locations, awards, lists, collections, movements):
   - Queries the corresponding table(s) via SQL.
   - Builds the document text (e.g. topic name + overview, or movie/series titles in different languages), truncated to stay inside OpenAI embedding limits (~32 000 characters).
   - Uses consistent ID patterns to identify documents in ChromaDB.
   - For **deleted or invalid records**, removes corresponding documents from ChromaDB.
   - For **existing records**, compares content and updates the document if it changed.
   - For **new records**, adds documents so ChromaDB can generate embeddings.
   - **Locations** are handled via a custom implementation: Wikidata items are fetched by joining `T_WC_WIKIDATA_ITEM_PROPERTY` (filtered on properties P840 — narrative location — and P915 — filming location) with `T_WC_T2S_ITEM`. Location document IDs use the Wikidata item ID (string) rather than a numeric primary key.
   - **Topics** include an extra deletion criterion: topics associated with only one movie or series have their embeddings removed.

4. **Cleans up orphaned embeddings**
   - Iterates over IDs in each collection.
   - Parses the ID back to the underlying primary key and language.
   - Checks if the row still exists in the source table.
   - Deletes any ChromaDB documents whose rows are missing.

5. **Stores runtime information**
   - Duration, reports, and last processed IDs are saved via `cp.f_setservervariable` so that the next run can resume intelligently.

## Running the script

From the project root:

```bash
python embedding-update.py
```

Before running, ensure that:

- **Environment**
  - `.env` exists and contains a valid `OPENAI_API_KEY`.
- **ChromaDB**
  - The Chroma HTTP server is running on `localhost:8100`.
- **Database**
  - The `citizenphil` module can connect to the database and the expected tables exist.

The script prints progress information (entity counts, added/updated/deleted documents) to stdout. It is intended to be run as a backend maintenance task rather than a user-facing application.

## Collections and ID conventions

Each collection uses a consistent document ID pattern:

- Topics: `topicid_<ID_TOPIC>_<LANG>` (bilingual EN/FR; overview appended to text)
- Movies: `movieid_<ID_MOVIE>_<LANG>` (EN, FR, and original language)
- Series: `serieid_<ID_SERIE>_<LANG>` (EN, FR, and original language)
- Persons: `personid_<ID_PERSON>_<LANG>` (single-language, English)
- Companies: `companyid_<ID_COMPANY>_<LANG>` (single-language, English)
- Networks: `networkid_<ID_NETWORK>_<LANG>` (single-language, English)
- Groups: `groupid_<ID_GROUP>_<LANG>` (bilingual EN/FR; non-numeric Wikidata-based ID)
- Locations: `locationid_<ID_ITEM>_<LANG>` (bilingual EN/FR; `ID_ITEM` is a Wikidata string ID, e.g. `Q84`)
- Awards: `awardid_<ID_AWARD>_<LANG>` (bilingual EN/FR)
- Lists: `listid_<ID_T2S_LIST>_<LANG>` (bilingual EN/FR)
- Collections: `collectionid_<ID_T2S_COLLECTION>_<LANG>` (bilingual EN/FR)
- Movements: `movementid_<ID_MOVEMENT>_<LANG>` (bilingual EN/FR)
- Deaths: `deathid_<ID_DEATH>_<LANG>` (bilingual EN/FR; overview appended to text)
- Nominations: `nominationid_<ID_NOMINATION>_<LANG>` (bilingual EN/FR; overview appended to text)

This convention allows the script to:

- Detect changes in content
- Delete documents when the DB row is deleted
- Resume processing from the last known ID

## Processes

The script runs one or more entity-specific processes selected via internal routing (stored in server variables) and executed as an ordered `process_id -> entity_name` mapping.

Current process IDs include:

| ID | Entity | Notes |
|----|--------|-------|
| 201 | topics | Bilingual EN/FR; deleted if movie+serie count ≤ 1 |
| 202 | movies | EN, FR, and original language via lang table |
| 203 | series | EN, FR, and original language via lang table |
| 204 | persons | Single-language (English) |
| 205 | companies | Single-language (English) |
| 206 | networks | Single-language (English) |
| 207 | ~~characters~~ | **Currently disabled** (mapped to 1207 in routing) |
| 208 | groups | Bilingual EN/FR; non-numeric Wikidata ID |
| 209 | locations | Bilingual EN/FR; custom join on `T_WC_WIKIDATA_ITEM_PROPERTY` filtered on P840 (narrative) and P915 (filming); Wikidata string ID |
| 210 | awards | Bilingual EN/FR |
| 211 | lists | Bilingual EN/FR |
| 212 | collections | Bilingual EN/FR |
| 213 | movements | Bilingual EN/FR |
| 214 | deaths | Bilingual EN/FR; overview appended to text; Wikidata ID stored in metadata |
| 215 | nominations | Bilingual EN/FR; overview appended to text; Wikidata ID stored in metadata |

## Notes

- The script is optimized to avoid re-embedding unchanged content.
- There are commented blocks for special maintenance operations (e.g. batch deletes); those are not executed in normal runs.
 - If you modify the schema, collection names, or ID patterns, ensure you update `embedding-update.py` accordingly.
