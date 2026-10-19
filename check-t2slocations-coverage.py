"""Read-only coverage check of the t2slocations collection (EMBEDDING-UPDATE-013).

Recomputes, from T_WC_T2S_LOCATION, the document ids process 216 must hold, with 216's own
rules (one document per language, key t2slocationid_<ID_LOCATION>_<lang>; none for a deleted
place or an empty name; no French document when the French name equals the English one),
then asks ChromaDB which of them exist. Reports missing documents for all places and for the
places cited by episodes only (TMDB-MOVIE-PREPROCESS-062), plus documents Chroma holds that
216 would not write. Writes nothing, neither to Chroma nor to the database.

Run on the VPS, in the job's own image (it reaches Chroma on localhost:8100):
    cd ~/docker/embedding-update && git pull && docker build -t embedding-update-python-app .
    docker run --rm --network=host --env-file .env embedding-update-python-app python check-t2slocations-coverage.py
"""
import chromadb
import citizenphil as cp

COLLECTION = "t2slocations"
BATCH = 500


def expected_doc_ids(rows):
    ids = {}
    for row in rows:
        if (row.get("DELETED") or 0) == 1:
            continue
        name_en = (row.get("LOCATION_NAME") or "").strip()
        name_fr = (row.get("LOCATION_NAME_FR") or "").strip()
        key = row["ID_LOCATION"]
        if name_en:
            ids[f"t2slocationid_{key}_en"] = row
        if name_fr and name_fr != name_en:
            ids[f"t2slocationid_{key}_fr"] = row
    return ids


def main():
    connection = cp.f_getconnection()
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT ID_LOCATION, LOCATION_NAME, LOCATION_NAME_FR, DELETED, "
            "COALESCE(MOVIE_COUNT, 0) AS MOVIE_COUNT, COALESCE(SERIE_COUNT, 0) AS SERIE_COUNT, "
            "COALESCE(EPISODE_COUNT, 0) AS EPISODE_COUNT FROM T_WC_T2S_LOCATION"
        )
        rows = cursor.fetchall()
    expected = expected_doc_ids(rows)

    collection = chroma_collection()
    present = set()
    wanted = sorted(expected)
    for offset in range(0, len(wanted), BATCH):
        got = collection.get(ids=wanted[offset:offset + BATCH], include=[])
        present.update(got.get("ids") or [])

    all_ids = set()
    total = collection.count()
    for offset in range(0, total, 5000):
        got = collection.get(limit=5000, offset=offset, include=[])
        all_ids.update(got.get("ids") or [])

    missing = [doc_id for doc_id in wanted if doc_id not in present]
    episode_only = {doc_id for doc_id, row in expected.items()
                    if row["EPISODE_COUNT"] > 0 and row["MOVIE_COUNT"] == 0 and row["SERIE_COUNT"] == 0}
    missing_episode_only = [doc_id for doc_id in missing if doc_id in episode_only]
    extra = sorted(all_ids - set(expected))

    print(f"collection {COLLECTION}: {total} documents")
    print(f"expected from T_WC_T2S_LOCATION: {len(expected)} "
          f"({sum(i.endswith('_en') for i in expected)} en, {sum(i.endswith('_fr') for i in expected)} fr)")
    print(f"missing: {len(missing)}")
    print(f"episode-only places: {len(episode_only)} expected documents, {len(missing_episode_only)} missing")
    print(f"in Chroma but not expected (216 would remove them): {len(extra)}")
    for doc_id in missing[:20]:
        print(f"  MISSING {doc_id}")
    for doc_id in extra[:20]:
        print(f"  EXTRA   {doc_id}")


def chroma_collection():
    # get_collection, never get_or_create: the HNSW configuration of t2slocations is set by
    # embedding-update.py alone (AGENTS.md), and no embedding function is needed for get().
    client = chromadb.HttpClient(host="localhost", port=8100)
    return client.get_collection(name=COLLECTION)


if __name__ == "__main__":
    main()
