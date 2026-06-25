"""
One-time backfill: add a numeric ``year`` metadata to every existing document of
the ``movies`` ChromaDB collection, WITHOUT recomputing any embedding.

Why
---
Movie title docs currently carry no metadata (the movie indexer in
``embedding-update.py`` writes ``documents`` only). Without a ``year`` metadata,
the entity resolver cannot apply a ``where={"year": {...}}`` filter to
disambiguate same-title films (e.g. "Le Bonheur" 1934 vs 1965). This script
patches metadata in place:

    collection.update(ids=..., metadatas=...)   # NO documents arg

Because no ``documents`` are passed, ChromaDB does NOT re-embed: the existing
vectors are untouched and there is zero OpenAI cost. (Confirmed against the
Chroma docs: metadata-only update.)

Design notes
------------
- Doc id format: ``movieid_<ID_MOVIE>_<langcode>`` -- one doc per language
  variant. Every language doc of a movie gets the same year.
- Year is stored as an ``int`` (not a string) so range filters ``$gte/$lte``
  work and metadata stays type-consistent across the collection.
- ChromaDB rejects ``None`` metadata values. Movies whose ``RELEASE_YEAR`` is
  NULL/invalid are LEFT WITHOUT a ``year`` key (not set to None). Consequence:
  the resolver's year filter MUST stay optional, with an unfiltered fallback,
  or those movies become unreachable through the filtered path.
- Idempotent: re-running skips docs already carrying the right year.
- Metadata-only updates never change collection size or doc order, so
  paginating by offset while updating in the same pass is safe.

Run
---
    python backfill-movie-year.py            # full backfill
    python backfill-movie-year.py --dry-run  # report only, write nothing
"""

import os
import sys
from dotenv import load_dotenv
import chromadb
import pymysql.cursors
import citizenphil as cp

load_dotenv()

CHROMADB_HOST = os.getenv("CHROMADB_HOST", "localhost")
CHROMADB_PORT = int(os.getenv("CHROMADB_PORT", "8100"))
COLLECTION_NAME = "movies"
BATCH_SIZE = 1000

MOVIE_TABLE = "T_WC_T2S_MOVIE"
ID_COLUMN = "ID_MOVIE"
YEAR_COLUMN = "RELEASE_YEAR"  # if absent in your schema, swap for YEAR(DAT_RELEASE)

DRY_RUN = "--dry-run" in sys.argv

# Metadata-only updates never embed, so no embedding_function is required here.
chroma_client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
movies = chroma_client.get_or_create_collection(name=COLLECTION_NAME)

conn = cp.f_getconnection()


def parse_movie_id(docid):
    """movieid_<ID_MOVIE>_<lang> -> int ID_MOVIE, or None if the id is not a movie doc."""
    parts = str(docid).split("_")
    if len(parts) < 3 or parts[0] != "movieid":
        return None
    raw = parts[1]
    if not raw.isdigit():
        return None
    return int(raw)


def fetch_years(movie_ids):
    """Return {ID_MOVIE: year_int} for the given ids, skipping NULL/invalid years."""
    if not movie_ids:
        return {}
    ids = list(movie_ids)
    placeholders = ",".join(["%s"] * len(ids))
    sql = (
        "SELECT " + ID_COLUMN + ", " + YEAR_COLUMN
        + " FROM " + MOVIE_TABLE
        + " WHERE " + ID_COLUMN + " IN (" + placeholders + ")"
    )
    out = {}
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute(sql, ids)
        for row in cur.fetchall():
            year = row.get(YEAR_COLUMN)
            if year is None:
                continue
            try:
                out[int(row[ID_COLUMN])] = int(year)
            except (TypeError, ValueError):
                continue
    return out


def main():
    offset = 0
    processed = updated = skipped_no_year = skipped_unchanged = skipped_not_movie = 0

    while True:
        batch = movies.get(include=["metadatas"], limit=BATCH_SIZE, offset=offset)
        ids = batch.get("ids") or []
        if not ids:
            break
        metadatas = batch.get("metadatas") or [None] * len(ids)

        # Resolve the distinct movie ids in this batch in a single DB round-trip.
        doc_movie = {}
        for docid in ids:
            mid = parse_movie_id(docid)
            if mid is not None:
                doc_movie[docid] = mid
        years = fetch_years(set(doc_movie.values()))

        upd_ids, upd_meta = [], []
        for docid, md in zip(ids, metadatas):
            processed += 1
            mid = doc_movie.get(docid)
            if mid is None:
                skipped_not_movie += 1
                continue
            year = years.get(mid)
            if year is None:
                skipped_no_year += 1
                continue
            md = dict(md or {})
            if md.get("year") == year:
                skipped_unchanged += 1
                continue
            md["year"] = year  # int -> numeric range filters work
            upd_ids.append(docid)
            upd_meta.append(md)

        if upd_ids and not DRY_RUN:
            # No `documents` -> embeddings are preserved, no OpenAI call.
            movies.update(ids=upd_ids, metadatas=upd_meta)
        updated += len(upd_ids)

        print(
            "offset=%d processed=%d updated=%d no_year=%d unchanged=%d not_movie=%d"
            % (offset, processed, updated, skipped_no_year, skipped_unchanged, skipped_not_movie)
        )

        if len(ids) < BATCH_SIZE:
            break
        offset += BATCH_SIZE

    print("---")
    print(
        "%s docs=%d updated=%d skipped_no_year=%d skipped_unchanged=%d skipped_not_movie=%d"
        % (
            "DRY-RUN (nothing written)." if DRY_RUN else "DONE.",
            processed, updated, skipped_no_year, skipped_unchanged, skipped_not_movie,
        )
    )


if __name__ == "__main__":
    main()
