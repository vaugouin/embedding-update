# deduplicate-embeddings.py

## Purpose

Previous versions of `embedding-update.py` created one ChromaDB embedding per language for each entity, even when the English and French labels were identical. This left redundant vectors in every collection — two documents with the same text but different IDs (e.g. `personid_42_en` and `personid_42_fr`).

This script is a **one-off cleanup** that scans every collection and deletes those duplicates. It keeps the English (`_en`) embedding as the canonical one and removes any other language variant whose document text is exactly identical to it.

`embedding-update.py` was updated to skip duplicate embeddings at creation time, so this script only needs to be run once to clean up data produced by earlier runs.

## How it works

For each collection, the script:

1. Iterates all documents in batches of 1000.
2. For every document whose ID does **not** end in `_en`, fetches the corresponding `_en` document.
3. If both documents exist and their text is **exactly equal**, the non-English document is deleted.

The comparison is done on the stored document text in ChromaDB — no database or API call is needed beyond the ChromaDB HTTP client.

## Requirements

Same environment as `embedding-update.py`:

- Python dependencies: `chromadb`, `openai`, `numpy`, `python-dotenv`
- A `.env` file with `OPENAI_API_KEY` set (required to initialise the embedding function when opening collections)
- ChromaDB running on `localhost:8100`

## Usage

```bash
python deduplicate-embeddings.py
```

The script prints each duplicate it finds before deleting it, and prints a per-collection summary and a final total at the end.

Example output:

```
--- Collection: persons ---
  Duplicate: personid_42_fr == personid_42_en -> will delete
  Scanned 1500 non-English documents, deleted 1 duplicates.

--- Collection: movies ---
  Scanned 3200 non-English documents, deleted 47 duplicates.

...

Done. Total scanned: 28400, total deleted: 53.
```

## Safety notes

- Only **exact** text matches are deleted. Entities whose French label differs even slightly from the English label are left untouched.
- The canonical `_en` embedding is never deleted.
- The script is idempotent: running it a second time will find nothing to delete.
