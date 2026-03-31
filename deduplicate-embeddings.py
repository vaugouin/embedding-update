import os
import chromadb
import numpy as np
import openai
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables. Please check your .env file.")

class OpenAIEmbeddingFunction:
    def __init__(self, model="text-embedding-3-large"):
        self.model = model

    def __call__(self, input):
        response = openai.embeddings.create(input=input, model=self.model)
        embeddings = [item.embedding for item in response.data]
        return [np.array(embedding) for embedding in embeddings]

    def name(self):
        return f"openai_{self.model.replace('-', '_')}"

COLLECTION_NAMES = [
    "persons",
    "movies",
    "series",
    "companies",
    "networks",
    "topics",
    "locations",
    "groups",
    "characters",
    "lists",
    "collections",
    "deaths",
    "awards",
    "nominations",
    "movements",
]

CANONICAL_LANG = "en"
BATCH_SIZE = 1000

chroma_client = chromadb.HttpClient(host="localhost", port=8100)
embedding_function = OpenAIEmbeddingFunction(model="text-embedding-3-large")

total_deleted = 0
total_scanned = 0

for collection_name in COLLECTION_NAMES:
    collection = chroma_client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedding_function
    )

    deleted_count = 0
    scanned_count = 0
    offset = 0

    print(f"\n--- Collection: {collection_name} ---")

    while True:
        results = collection.get(include=["documents"], limit=BATCH_SIZE, offset=offset)
        ids = results["ids"]
        documents = results["documents"]

        if not ids:
            break

        ids_to_delete = []

        for doc_id, doc_text in zip(ids, documents):
            parts = doc_id.rsplit("_", 1)
            if len(parts) != 2:
                continue

            base_id, lang_code = parts
            if lang_code == CANONICAL_LANG:
                continue

            scanned_count += 1
            canonical_id = base_id + "_" + CANONICAL_LANG

            canonical_result = collection.get(ids=[canonical_id], include=["documents"])
            if not canonical_result["ids"]:
                continue

            canonical_text = canonical_result["documents"][0]
            if doc_text == canonical_text:
                ids_to_delete.append(doc_id)
                print(f"  Duplicate: {doc_id} == {canonical_id} -> will delete")

        if ids_to_delete:
            collection.delete(ids=ids_to_delete)
            deleted_count += len(ids_to_delete)

        if len(ids) < BATCH_SIZE:
            break
        offset += BATCH_SIZE

    print(f"  Scanned {scanned_count} non-English documents, deleted {deleted_count} duplicates.")
    total_deleted += deleted_count
    total_scanned += scanned_count

print(f"\nDone. Total scanned: {total_scanned}, total deleted: {total_deleted}.")
