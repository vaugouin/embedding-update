import pandas as pd
import numpy as np
import openai
import os
from dotenv import load_dotenv
import chromadb
#from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
#pip install psutil
import psutil
import pymysql.cursors
import citizenphil as cp
from datetime import datetime, timedelta
import time

def f_logmemory(strlabel=""):
    """Print host RAM + swap state for crash diagnostics.

    Runs inside the container, but with no cgroup memory limit set psutil
    reports host-wide figures. Used to document HNSW load failures, which on
    this VPS stem from RAM exhaustion (index must fit entirely in RAM) rather
    than on-disk corruption.
    """
    try:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        print(
            f"[MEM] {strlabel} | RAM available {mem.available / 1024**3:.2f} GiB / "
            f"{mem.total / 1024**3:.2f} GiB ({mem.percent:.0f}% used) | "
            f"swap free {swap.free / 1024**3:.2f} GiB / {swap.total / 1024**3:.2f} GiB"
        )
    except Exception as exc:
        print(f"[MEM] {strlabel} | memory probe failed: {exc}")

# Load environment variables from .env file
load_dotenv()

# Set your OpenAI API key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

# Validate that the API key was loaded
if not openai.api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables. Please check your .env file.")

class OpenAIEmbeddingFunction:
    def __init__(self, model="text-embedding-3-large"):
        """Initialize with the given OpenAI embedding model name."""
        self.model = model

    def __call__(self, input):
        """Generate embeddings for a list of texts using OpenAI's embedding model."""
        response = openai.embeddings.create(
            input=input, # Ensure parameter name matches ChromaDB's expectations
            model=self.model
        )
        # Convert to numpy arrays for ChromaDB compatibility
        embeddings = [item.embedding for item in response.data]
        return [np.array(embedding) for embedding in embeddings]
    
    def name(self):
        """Return the name of the embedding function for ChromaDB compatibility."""
        return f"openai_{self.model.replace('-', '_')}"

# Initialize ChromaDB with persistent storage
chroma_client = chromadb.HttpClient(host="localhost", port=8100)

# Initialize ChromaDB with OpenAI's embedding function
embedding_function = OpenAIEmbeddingFunction(model="text-embedding-3-large")

print("ChromaDB initialized with a text-embedding-3-large model.")

# Get the virtual memory details
memory_info = psutil.virtual_memory()
# Print the available memory
print("Démarrage de l'API")
print(f"Total Memory: {memory_info.total / (1024 ** 3):.2f} GB")
print(f"Available Memory: {memory_info.available / (1024 ** 3):.2f} GB")
print(f"Used Memory: {memory_info.used / (1024 ** 3):.2f} GB")
print(f"Free Memory: {memory_info.free / (1024 ** 3):.2f} GB")
print(f"Memory Usage: {memory_info.percent}%")

# In your Python script, add this to see collection info:
print("---------------")
collections = chroma_client.list_collections()
for collection in collections:
    print(f"Collection name: {collection.name}")
    print(f"Collection ID: {collection.id}")
    print(f"Collection metadata: {collection.metadata}")
print("---------------")

strservervariableprefix = "strembeddingupdate"
strservervariablenameprocessesexecuted = strservervariableprefix + "processesexecuted"
strservervariablenameprocessesexecutedprevious = strservervariableprefix + "processesexecutedprevious"
strprocessesexecutedprevious = cp.f_getservervariable(strservervariablenameprocessesexecuted,0)
strprocessesexecuteddesc = "List of processes executed in the embedding update process"
cp.f_setservervariable(strservervariablenameprocessesexecutedprevious,strprocessesexecutedprevious,strprocessesexecuteddesc + " (previous execution)",0)
strprocessesexecuted = ""
cp.f_setservervariable(strservervariablenameprocessesexecuted,strprocessesexecuted,strprocessesexecuteddesc,0)

# Create or load entity collections with the custom embedding function
CHROMADB_COLLECTIONS_BY_NAME = {
    name: chroma_client.get_or_create_collection(name=name, embedding_function=embedding_function)
    # "locations" (keyed on the QID) is gone since 2026-10-09 too: it served API 1.1.18 only,
    # retired with Blue; places are embedded in t2slocations by process 216 (EMBEDDING-UPDATE-010).
    # "persons" is gone since 2026-10-09: fastapi-text2sql resolves person names with rapidfuzz on
    # T_WC_T2S_PERSON and T_WC_T2S_PERSON_ALSO_KNOWN_AS and never queried this collection, so
    # process 204 paid OpenAI embeddings for nothing. Listing it here would recreate it empty, and
    # bringing 204 back would re-embed every person: do neither without a reader for it.
    for name in [
        "movies",
        "series",
        "companies",
        "networks",
        "topics",
        "groups",
        "characters",
        "lists",
        "collections",
        "deaths",
        "awards",
        "nominations",
        "movements",
    ]
}

topics = CHROMADB_COLLECTIONS_BY_NAME["topics"]
movies = CHROMADB_COLLECTIONS_BY_NAME["movies"]
series = CHROMADB_COLLECTIONS_BY_NAME["series"]
companies = CHROMADB_COLLECTIONS_BY_NAME["companies"]
networks = CHROMADB_COLLECTIONS_BY_NAME["networks"]
characters = CHROMADB_COLLECTIONS_BY_NAME["characters"]
groups = CHROMADB_COLLECTIONS_BY_NAME["groups"]
lists = CHROMADB_COLLECTIONS_BY_NAME["lists"]
collections = CHROMADB_COLLECTIONS_BY_NAME["collections"]
deaths = CHROMADB_COLLECTIONS_BY_NAME["deaths"]
awards = CHROMADB_COLLECTIONS_BY_NAME["awards"]
nominations = CHROMADB_COLLECTIONS_BY_NAME["nominations"]
movements = CHROMADB_COLLECTIONS_BY_NAME["movements"]

# t2slocations : la collection des lieux lue depuis le read-model T_WC_T2S_LOCATION
# (EMBEDDING-UPDATE-005). CREEE ICI ET NULLE PART AILLEURS, avec une configuration
# explicite. Les quinze autres collections vivent sur les defauts du serveur, qui peuvent
# bouger avec l'image chromadb/chroma (non epinglee) ; celle-ci ecrit les siens.
# fastapi-text2sql et embedding-query doivent la LIRE (get_collection), pas la creer : le
# premier get_or_create fixe la configuration pour toujours, et `space` ne se change plus.
#   space           l2  : le meme que les quinze autres. Les vecteurs de text-embedding-3-large
#                         sont de norme 1, donc l2, cosine et ip rendent le meme classement ;
#                         seule l'echelle de la distance differe, et rien dans la pile ne
#                         raisonne sur la distance (la resolution classe les dix premiers par
#                         ratio rapidfuzz). Passer une collection en cosine la rendrait
#                         incomparable aux autres ; si un jour on veut cosine, c'est pour toutes.
#   ef_search       100 : la resolution a besoin de la correspondance exacte dans les dix
#                         premiers ; un ef_search bas la manque (doc Chroma, mesure sur un
#                         exact match present et non rendu).
#   ef_construction 100, max_neighbors 16 : les defauts hnswlib, ecrits pour etre lus.
T2SLOCATIONS_HNSW_CONFIGURATION = {"space": "l2", "ef_construction": 100, "ef_search": 100, "max_neighbors": 16}

# Le mot de type ecrit dans le document d'un lieu, dans la langue du document. Les sept
# valeurs sont celles que le processus 72 de tmdb-movie-preprocess ecrit dans LOCATION_TYPE
# (LOCATION_TYPE_CONES) ; une valeur inconnue est ecrite telle quelle.
ARR_T2SLOCATION_TYPE_LABEL = {
    "en": {"fiction": "fictional place", "country": "country", "city": "city", "island": "island",
           "structure": "structure", "nature": "natural feature", "region": "region"},
    "fr": {"fiction": "lieu de fiction", "country": "pays", "city": "ville", "island": "île",
           "structure": "structure", "nature": "site naturel", "region": "région"},
}

def f_getorcreatet2slocationscollection(strname="t2slocations", strprocess="216"):
    """Get or create a read-model collection (`t2slocations` by default) with an explicit HNSW configuration.

    Also serves `t2ssourceworks` (process 217, EMBEDDING-UPDATE-011): same configuration, same
    reasons, only the name and the process number of the messages change.

    Tries the 1.x ``configuration=`` parameter first and falls back to the legacy
    ``metadata={"hnsw:*"}`` keys on an older client. On an existing collection both forms
    are ignored by Chroma, so the configuration is read back and printed on every run, and a
    ``space`` other than the expected one is reported loudly. Never raises: a failure here
    must not take the fifteen other collections down with it, so it returns ``None`` and
    the process that reads it skips the run.
    """
    try:
        try:
            chromacollection = chroma_client.get_or_create_collection(
                name=strname,
                embedding_function=embedding_function,
                configuration={"hnsw": dict(T2SLOCATIONS_HNSW_CONFIGURATION)},
            )
        except TypeError:
            # Client anterieur a 1.0 : pas de parametre configuration ; les cles hnsw:* de
            # metadata font le meme travail.
            chromacollection = chroma_client.get_or_create_collection(
                name=strname,
                embedding_function=embedding_function,
                metadata={
                    "hnsw:space": T2SLOCATIONS_HNSW_CONFIGURATION["space"],
                    "hnsw:construction_ef": T2SLOCATIONS_HNSW_CONFIGURATION["ef_construction"],
                    "hnsw:search_ef": T2SLOCATIONS_HNSW_CONFIGURATION["ef_search"],
                    "hnsw:M": T2SLOCATIONS_HNSW_CONFIGURATION["max_neighbors"],
                },
            )
    except Exception as exc:
        print(f"⚠ {strname}: collection unavailable ({exc}); process {strprocess} will be skipped this run.")
        return None
    arrconfiguration = getattr(chromacollection, "configuration_json", None)
    if callable(arrconfiguration):
        try:
            arrconfiguration = arrconfiguration()
        except Exception:
            arrconfiguration = None
    arrmetadata = getattr(chromacollection, "metadata", None)
    print(f"{strname} configuration: {arrconfiguration if arrconfiguration is not None else arrmetadata}")
    strspace = None
    if isinstance(arrconfiguration, dict):
        arrhnsw = arrconfiguration.get("hnsw")
        if isinstance(arrhnsw, dict):
            strspace = arrhnsw.get("space")
    if strspace is None and isinstance(arrmetadata, dict):
        strspace = arrmetadata.get("hnsw:space")
    if strspace is not None and strspace != T2SLOCATIONS_HNSW_CONFIGURATION["space"]:
        print(f"⚠ {strname}: space is '{strspace}', expected '{T2SLOCATIONS_HNSW_CONFIGURATION['space']}'. "
              "The collection was created elsewhere with another configuration; space cannot be changed, drop and rebuild it.")
    return chromacollection

t2slocations = f_getorcreatet2slocationscollection()

# t2ssourceworks : the works movies and series are based on (Wikidata P144), read from the
# T_WC_T2S_SOURCE_WORK read-model built by tmdb-movie-preprocess process 73
# (TMDB-MOVIE-PREPROCESS-055). Same rules as t2slocations: created HERE only, with the same
# explicit configuration; fastapi-text2sql and embedding-query read it with get_collection.
# It lets the API resolve a Source_work_name ("Au coeur des tenebres", "Dracul", "Heart of
# Darkness") to the canonical name before the SQL runs (FASTAPI-TEXT2SQL-320, 2537 FR failed on
# a name compared in the wrong language).
t2ssourceworks = f_getorcreatet2slocationscollection("t2ssourceworks", "217")

# The words written in a source work's document, per language: the type, then the form when
# there is one. The values are those process 73 writes (SOURCE_WORK_TYPE_CONES); an unknown
# value is written as is.
ARR_T2SSOURCEWORK_TYPE_LABEL = {
    "en": {"literary": "literary work", "comic": "comic", "stage": "stage work", "game": "game",
           "screen": "film or series", "folklore": "tale", "other": "",
           "manga": "manga", "light_novel": "light novel", "play": "play", "musical": "musical"},
    "fr": {"literary": "œuvre littéraire", "comic": "bande dessinée", "stage": "œuvre de scène", "game": "jeu",
           "screen": "film ou série", "folklore": "conte", "other": "",
           "manga": "manga", "light_novel": "light novel", "play": "pièce de théâtre", "musical": "comédie musicale"},
}

#Anonymized queries collection
anonymizedqueries = chroma_client.get_or_create_collection(
    name="anonymizedqueries",
    embedding_function=embedding_function  # Custom embedding model
)

try:
    conn = cp.f_getconnection()
    with conn:
        with conn.cursor() as cursor:
            cursor2 = conn.cursor()
            # Start timing the script execution
            start_time = time.time()
            strprocessstart = datetime.now(cp.paris_tz).strftime("%Y-%m-%d %H:%M:%S")

            strservervariablenamestartdatetime = strservervariableprefix + "startdatetime"
            strservervariablenametotalruntime = strservervariableprefix + "totalruntime"
            strservervariablenametotalruntimeprevious = strservervariableprefix + "totalruntimeprevious"
            strservervariablenamecurrentcontent = strservervariableprefix + "currentcontent"
            cp.f_setservervariable(strservervariablenamestartdatetime,strprocessstart,"Date and time of the last start of the embedding update process",0)
            strtotalruntimedesc = "Total runtime of the embedding update process"
            strtotalruntimeprevious = cp.f_getservervariable(strservervariablenametotalruntime,0)
            cp.f_setservervariable(strservervariablenametotalruntimeprevious,strtotalruntimeprevious,strtotalruntimedesc + " (previous execution)",0)
            strtotalruntime = "RUNNING"
            cp.f_setservervariable(strservervariablenametotalruntime,strtotalruntime,strtotalruntimedesc,0)
            
            # Ensure text length is within text-embedding-3-large model limits (8191 tokens)
            # Approximate 4 characters per token, so limit to ~32,000 characters to be safe
            max_chars = 32000

            def f_process_bilingual_t2s_entity_embeddings(*, strentityname, strentitycollection, strtablename, strkeyfieldname, stroldid, strtitlefielden, strtitlefieldfr, chromacollection, stridrecordfield="ID_RECORD", extra_metadata_fields=None, id_is_numeric=True, overview_field="OVERVIEW", extra_select_fields=None, should_delete_row=None):
                """Sync bilingual (EN/FR) ChromaDB embeddings for a T2S entity table.

                Queries the database for rows updated since the last run (or from `stroldid`),
                then adds, updates, or deletes the corresponding ChromaDB documents for both
                the English and French titles. Appends the overview to the document text when
                available. After processing updates, sweeps the collection and removes any
                stale documents whose source row no longer exists in the database.

                Args:
                    strentityname: Short entity identifier used in doc IDs and server variables
                        (e.g. ``"topic"``).
                    strentitycollection: Human-readable collection label for log messages
                        (e.g. ``"topics"``).
                    strtablename: Source database table name.
                    strkeyfieldname: Primary-key column name in the source table.
                    stroldid: Resume from this ID value (empty string to start from the
                        beginning).
                    strtitlefielden: Column name for the English title.
                    strtitlefieldfr: Column name for the French title.
                    chromacollection: Target ChromaDB collection object.
                    stridrecordfield: Optional secondary record-ID column included in metadata.
                    extra_metadata_fields: Dict mapping metadata key → column name for
                        additional fields to store in ChromaDB metadata.
                    id_is_numeric: Whether the primary key is numeric (affects SQL quoting).
                    overview_field: Column name for the overview/description text appended to
                        the embedding document.
                    extra_select_fields: List of extra column names to SELECT (used by
                        ``should_delete_row``).
                    should_delete_row: Optional callable ``(row) -> bool``; when it returns
                        ``True`` the embedding is deleted even if ``DELETED`` is 0.
                """
                print("Create embeddings for the " + strentitycollection)

                strservervariablenameid = strservervariableprefix + strentityname + "id"
                strservervariablenamestartdatetime = strservervariableprefix + strentityname + "startdatetime"
                strservervariablenamedeletereport = strservervariableprefix + strentityname + "deletereport"
                strservervariablenamenotdeletereport = strservervariableprefix + strentityname + "notdeletereport"

                strstartdatetimeprevious = cp.f_getservervariable(strservervariablenamestartdatetime, 0)
                strprocessstartlocal = datetime.now(cp.paris_tz).strftime("%Y-%m-%d %H:%M:%S")

                strsql = ""
                strsql += "SELECT DISTINCT " + strkeyfieldname + ", "
                if stridrecordfield is not None and str(stridrecordfield).strip() != "":
                    strsql += stridrecordfield + ", "
                if extra_metadata_fields is not None:
                    for md_key, md_col in extra_metadata_fields.items():
                        if md_col is not None and str(md_col).strip() != "":
                            strsql += str(md_col) + ", "
                if extra_select_fields is not None:
                    for extra_col in extra_select_fields:
                        if extra_col is not None and str(extra_col).strip() != "":
                            strsql += str(extra_col) + ", "
                strsql += "'en' AS ENGLISH_LANGUAGE, " + strtitlefielden + ", 'fr' AS FRENCH_LANGUAGE, " + strtitlefieldfr + ", "
                if overview_field is not None and str(overview_field).strip() != "":
                    strsql += str(overview_field) + ", "
                strsql += "DELETED "
                strsql += "FROM " + strtablename + " "
                if stroldid != "":
                    if id_is_numeric:
                        strsql += "WHERE " + strkeyfieldname + " >= " + stroldid + " "
                    else:
                        stroldid_sql = str(stroldid).replace("'", "''")
                        strsql += "WHERE " + strkeyfieldname + " >= '" + stroldid_sql + "' "
                if strstartdatetimeprevious is not None and str(strstartdatetimeprevious).strip() != "":
                    strstartdatetimeprevious = str(strstartdatetimeprevious).strip().replace("'", "''")
                    if stroldid != "":
                        strsql += "AND TIM_UPDATED >= '" + strstartdatetimeprevious + "' "
                    else:
                        strsql += "WHERE TIM_UPDATED >= '" + strstartdatetimeprevious + "' "
                strsql += "ORDER BY " + strkeyfieldname + " ASC "
                print(strsql)
                try:
                    cursor.execute(strsql)
                except Exception:
                    strsql = ""
                    strsql += "SELECT DISTINCT " + strkeyfieldname + ", "
                    if stridrecordfield is not None and str(stridrecordfield).strip() != "":
                        strsql += stridrecordfield + ", "
                    if extra_metadata_fields is not None:
                        for md_key, md_col in extra_metadata_fields.items():
                            if md_col is not None and str(md_col).strip() != "":
                                strsql += str(md_col) + ", "
                    if extra_select_fields is not None:
                        for extra_col in extra_select_fields:
                            if extra_col is not None and str(extra_col).strip() != "":
                                strsql += str(extra_col) + ", "
                    strsql += "'en' AS ENGLISH_LANGUAGE, " + strtitlefielden + ", 'fr' AS FRENCH_LANGUAGE, " + strtitlefieldfr + ", "
                    if overview_field is not None and str(overview_field).strip() != "":
                        strsql += str(overview_field) + ", "
                    strsql += "DELETED "
                    strsql += "FROM " + strtablename + " "
                    if stroldid != "":
                        if id_is_numeric:
                            strsql += "WHERE " + strkeyfieldname + " >= " + stroldid + " "
                        else:
                            stroldid_sql = str(stroldid).replace("'", "''")
                            strsql += "WHERE " + strkeyfieldname + " >= '" + stroldid_sql + "' "
                    strsql += "ORDER BY " + strkeyfieldname + " ASC "
                    print(strsql)
                    cursor.execute(strsql)
                lngrowcount = cursor.rowcount
                print(f"{lngrowcount} lines")
                results = cursor.fetchall()
                for row in results:
                    lngentityid = row[strkeyfieldname]
                    lngrecordid = None
                    if stridrecordfield is not None and str(stridrecordfield).strip() != "":
                        lngrecordid = row.get(stridrecordfield)
                    cp.f_setservervariable(strservervariablenameid, str(lngentityid), f"Current {strentityname} ID in the embedding update process", 0)
                    arrlanguage = {}
                    arrtitle = {}
                    arrlanguage['en'] = (row.get('ENGLISH_LANGUAGE') or '').strip()
                    arrtitle['en'] = (row.get(strtitlefielden) or '').strip()
                    arrlanguage['fr'] = (row.get('FRENCH_LANGUAGE') or '').strip()
                    arrtitle['fr'] = (row.get(strtitlefieldfr) or '').strip()
                    stroverview = ""
                    if overview_field is not None and str(overview_field).strip() != "":
                        stroverview = (row.get(overview_field) or '').strip()
                        stroverview = stroverview.replace("\n", " ")
                    intdeleted = row.get('DELETED', 0)

                    strfirstlangfulldesc = None
                    for lang_code in arrlanguage.keys():
                        if lang_code in arrtitle and arrtitle[lang_code].strip() != "":
                            strdocid = strentityname + "id_" + str(lngentityid) + "_" + lang_code
                            strfulldesc = arrtitle[lang_code]
                            if stroverview != "":
                                strfulldesc += ": " + stroverview
                            if len(strfulldesc) > max_chars:
                                strfulldesc = strfulldesc[:max_chars] + "..."
                            if strfirstlangfulldesc is None:
                                strfirstlangfulldesc = strfulldesc
                            elif strfulldesc == strfirstlangfulldesc:
                                continue
                            print(strfulldesc)

                            existing_doc = chromacollection.get(ids=[strdocid])

                            should_delete_custom = False
                            if should_delete_row is not None:
                                try:
                                    should_delete_custom = bool(should_delete_row(row))
                                except Exception:
                                    should_delete_custom = False

                            if intdeleted == 1 or should_delete_custom:
                                chromacollection.delete(ids=[strdocid])
                                print(f"{strkeyfieldname}: {lngentityid}, {strfulldesc} -> DELETED")
                                continue

                            if existing_doc and len(existing_doc['ids']) > 0:
                                strdoctext = existing_doc['documents'][0]
                                if strdoctext == strfulldesc:
                                    continue

                            if existing_doc and len(existing_doc['ids']) > 0:
                                metadata = {"id": str(lngentityid), "language": lang_code}
                                if lngrecordid is not None:
                                    metadata["id_record"] = str(lngrecordid)
                                if extra_metadata_fields is not None:
                                    for md_key, md_col in extra_metadata_fields.items():
                                        metadata[md_key] = row.get(md_col)
                                chromacollection.update(
                                    ids=[strdocid],
                                    documents=[strfulldesc],
                                    metadatas=[metadata]
                                )
                                print(f"{strkeyfieldname}: {lngentityid}, {strfulldesc} -> UPDATED")
                            else:
                                metadata = {"id": str(lngentityid), "language": lang_code}
                                if lngrecordid is not None:
                                    metadata["id_record"] = str(lngrecordid)
                                if extra_metadata_fields is not None:
                                    for md_key, md_col in extra_metadata_fields.items():
                                        metadata[md_key] = row.get(md_col)
                                chromacollection.add(
                                    ids=[strdocid],
                                    documents=[strfulldesc],
                                    metadatas=[metadata]
                                )
                                print(f"{strkeyfieldname}: {lngentityid}, {strfulldesc} -> ADDED")

                print(f"Delete all {strentityname} embeddings that do not exist anymore in the {strtablename} table")
                f_logmemory(f"before {strentityname} cleanup")
                try:
                    lngcollectioncount = chromacollection.count()
                    print(f"{strentityname} collection holds {lngcollectioncount} docs")
                except Exception as exc:
                    print(f"Could not count {strentityname} collection: {exc}")
                batch_size = 1000
                offset = 0
                lngdeletedcount = 0
                lngnondeletedcount = 0
                while True:
                    try:
                        results = chromacollection.get(include=[], limit=batch_size, offset=offset)
                    except Exception as exc:
                        print(f"[CHROMA] get() failed on {strentityname} at offset {offset}: {exc}")
                        f_logmemory(f"at {strentityname} get() failure")
                        raise
                    ids = results["ids"]
                    if not ids:
                        break
                    for id in ids:
                        parts = id.split('_')
                        if len(parts) < 3:
                            continue
                        docentity = parts[0]
                        docid = parts[1]
                        doclang = parts[2]
                        if docentity != strentityname + "id":
                            continue
                        if id_is_numeric:
                            if not str(docid).isdigit():
                                continue
                            strsql = "SELECT " + strkeyfieldname + " FROM " + strtablename + " WHERE " + strkeyfieldname + " = " + docid + " "
                        else:
                            docid_sql = str(docid).replace("'", "''")
                            strsql = "SELECT " + strkeyfieldname + " FROM " + strtablename + " WHERE " + strkeyfieldname + " = '" + docid_sql + "' "
                        cursor.execute(strsql)
                        lngrowcount = cursor.rowcount
                        if lngrowcount == 0:
                            chromacollection.delete(ids=[id])
                            print(f"Deleted {id} ")
                            lngdeletedcount += 1
                        else:
                            print(f"Not deleted {id} ")
                            lngnondeletedcount += 1
                    if len(ids) < batch_size:
                        break
                    offset += batch_size
                print(f"Deleted {lngdeletedcount} {strentityname} docs")
                print(f"Not deleted {lngnondeletedcount} {strentityname} docs")
                cp.f_setservervariable(strservervariablenamedeletereport, f"Deleted {lngdeletedcount} {strentityname} docs (enabled)", "", 0)
                cp.f_setservervariable(strservervariablenamenotdeletereport, f"Not deleted {lngnondeletedcount} {strentityname} docs", "", 0)
                cp.f_setservervariable(strservervariablenameid, "", f"Current {strentityname} ID in the embedding update process", 0)
                cp.f_setservervariable(strservervariablenamestartdatetime, strprocessstartlocal, f"Date and time of the last start of the {strentityname} embedding update process", 0)

            def f_process_en_fr_original_title_embeddings_from_lang_table(*, strentityname, strentitycollection, strtablename, strtablelang, strkeyfieldname, stroldid, chromacollection, strtitlefielden, strtitlefieldfr, stroriginal_language_field, stroriginal_title_field, stryearfield=None, id_is_numeric=True):
                """Sync EN, FR, and original-language ChromaDB embeddings using a joined language table.

                Queries the main entity table joined with a separate language/translation table
                to obtain the English title, French title, and original-language title for each
                entity. Creates one ChromaDB document per language variant (EN, FR, and the
                original language when different). Entities without a Wikidata ID are treated as
                deleted. After processing updates, sweeps the collection and removes stale
                documents whose source row no longer exists in the database.

                Unlike ``f_process_bilingual_t2s_entity_embeddings``, this function does not
                append an overview to the document text.

                Args:
                    strentityname: Short entity identifier used in doc IDs and server variables
                        (e.g. ``"movie"``).
                    strentitycollection: Human-readable collection label for log messages.
                    strtablename: Main entity database table name.
                    strtablelang: Language/translation table joined to the main table.
                    strkeyfieldname: Primary-key column name shared by both tables.
                    stroldid: Resume from this ID value (empty string to start from the
                        beginning).
                    chromacollection: Target ChromaDB collection object.
                    strtitlefielden: Column name for the English title in the main table.
                    strtitlefieldfr: Column name for the French title in the language table.
                    stroriginal_language_field: Column name for the original language code.
                    stroriginal_title_field: Column name for the original-language title.
                    id_is_numeric: Whether the primary key is numeric (affects SQL quoting).
                """
                print("Create embeddings for the " + strentitycollection)

                strservervariablenameid = strservervariableprefix + strentityname + "id"
                strservervariablenamestartdatetime = strservervariableprefix + strentityname + "startdatetime"
                strservervariablenamedeletereport = strservervariableprefix + strentityname + "deletereport"
                strservervariablenamenotdeletereport = strservervariableprefix + strentityname + "notdeletereport"

                strstartdatetimeprevious = cp.f_getservervariable(strservervariablenamestartdatetime, 0)
                strprocessstartlocal = datetime.now(cp.paris_tz).strftime("%Y-%m-%d %H:%M:%S")

                # Optional numeric metadata (e.g. RELEASE_YEAR for movies) added to each
                # ChromaDB doc so the resolver can disambiguate same-title entities with a
                # year filter. Selected as YEAR_VALUE; left out entirely when not requested.
                stryearselect = ""
                if stryearfield:
                    stryearselect = ", " + strtablename + "." + stryearfield + " AS YEAR_VALUE "

                strsql = "SELECT DISTINCT " + strtablename + "." + strkeyfieldname + ", " + strtablename + ".ID_WIKIDATA, 'en' AS ENGLISH_LANGUAGE, " + strtablename + "." + strtitlefielden + " AS ENGLISH_TITLE, " + strtablename + "." + stroriginal_language_field + ", " + strtablename + "." + stroriginal_title_field + ", " + strtablelang + ".LANG AS FRENCH_LANGUAGE, " + strtablelang + "." + strtitlefieldfr + " AS FRENCH_TITLE, " + strtablename + ".DELETED " + stryearselect
                strsql += "FROM " + strtablename + " "
                strsql += "LEFT JOIN " + strtablelang + " ON " + strtablename + "." + strkeyfieldname + " = " + strtablelang + "." + strkeyfieldname + " "
                strsql += "WHERE " + strtablelang + ".LANG = 'fr' "
                if stroldid != "":
                    if id_is_numeric:
                        strsql += "AND " + strtablename + "." + strkeyfieldname + " >= " + stroldid + " "
                    else:
                        stroldid_sql = str(stroldid).replace("'", "''")
                        strsql += "AND " + strtablename + "." + strkeyfieldname + " >= '" + stroldid_sql + "' "
                if strstartdatetimeprevious is not None and str(strstartdatetimeprevious).strip() != "":
                    strstartdatetimeprevious = str(strstartdatetimeprevious).strip().replace("'", "''")
                    strsql += "AND " + strtablename + ".TIM_UPDATED >= '" + strstartdatetimeprevious + "' "
                strsql += "ORDER BY " + strtablename + "." + strkeyfieldname + " ASC "
                try:
                    cursor.execute(strsql)
                except Exception:
                    strsql = "SELECT DISTINCT " + strtablename + "." + strkeyfieldname + ", " + strtablename + ".ID_WIKIDATA, 'en' AS ENGLISH_LANGUAGE, " + strtablename + "." + strtitlefielden + " AS ENGLISH_TITLE, " + strtablename + "." + stroriginal_language_field + ", " + strtablename + "." + stroriginal_title_field + ", " + strtablelang + ".LANG AS FRENCH_LANGUAGE, " + strtablelang + "." + strtitlefieldfr + " AS FRENCH_TITLE, " + strtablename + ".DELETED " + stryearselect
                    strsql += "FROM " + strtablename + " "
                    strsql += "LEFT JOIN " + strtablelang + " ON " + strtablename + "." + strkeyfieldname + " = " + strtablelang + "." + strkeyfieldname + " "
                    strsql += "WHERE " + strtablelang + ".LANG = 'fr' "
                    if stroldid != "":
                        if id_is_numeric:
                            strsql += "AND " + strtablename + "." + strkeyfieldname + " >= " + stroldid + " "
                        else:
                            stroldid_sql = str(stroldid).replace("'", "''")
                            strsql += "AND " + strtablename + "." + strkeyfieldname + " >= '" + stroldid_sql + "' "
                    strsql += "ORDER BY " + strtablename + "." + strkeyfieldname + " ASC "
                    cursor.execute(strsql)
                lngrowcount = cursor.rowcount
                print(f"{lngrowcount} lines")
                results = cursor.fetchall()
                for row in results:
                    lngentityid = row[strkeyfieldname]
                    cp.f_setservervariable(strservervariablenameid, str(lngentityid), f"Current {strentityname} ID in the embedding update process", 0)
                    strwikidataid = (row.get('ID_WIKIDATA') or '').strip()
                    metadata_year = None
                    if stryearfield:
                        try:
                            _yr = row.get('YEAR_VALUE')
                            metadata_year = int(_yr) if _yr is not None else None
                        except (TypeError, ValueError):
                            metadata_year = None
                    arrlanguage = {}
                    arrtitle = {}
                    arrlanguage['en'] = (row.get('ENGLISH_LANGUAGE') or '').strip()
                    arrtitle['en'] = (row.get('ENGLISH_TITLE') or '').strip()
                    arrlanguage['fr'] = (row.get('FRENCH_LANGUAGE') or '').strip()
                    arrtitle['fr'] = (row.get('FRENCH_TITLE') or '').strip()
                    strlang = (row.get(stroriginal_language_field) or '').strip()
                    if strlang != "" and strlang not in arrlanguage:
                        arrtitle[strlang] = (row.get(stroriginal_title_field) or '').strip()
                        arrlanguage[strlang] = strlang
                    intdeleted = row.get('DELETED', 0)
                    if strwikidataid == "":
                        intdeleted = 1

                    strfirstlangfulldesc = None
                    for lang_code in arrlanguage.keys():
                        if lang_code in arrtitle and arrtitle[lang_code].strip() != "":
                            strtitle = arrtitle[lang_code].strip()
                            strlangcode = arrlanguage[lang_code].strip()
                            strdocid = strentityname + "id_" + str(lngentityid) + "_" + strlangcode
                            strfulldesc = strtitle
                            if strfirstlangfulldesc is None:
                                strfirstlangfulldesc = strfulldesc
                            elif strfulldesc == strfirstlangfulldesc:
                                continue

                            existing_doc = chromacollection.get(ids=[strdocid])

                            if intdeleted == 1:
                                if existing_doc and len(existing_doc['ids']) > 0:
                                    chromacollection.delete(ids=[strdocid])
                                    print(f"{strkeyfieldname}: {lngentityid}, {strfulldesc} ({strlangcode}) -> DELETED")
                                continue

                            if existing_doc and len(existing_doc['ids']) > 0:
                                strdoctext = existing_doc['documents'][0]
                                if strdoctext == strfulldesc:
                                    continue

                            # Attach year metadata only when available (ChromaDB rejects None);
                            # documents are passed too, so this doc is (re)embedded as before.
                            extra_kwargs = {"metadatas": [{"year": metadata_year}]} if metadata_year is not None else {}
                            if existing_doc and len(existing_doc['ids']) > 0:
                                chromacollection.update(
                                    ids=[strdocid],
                                    documents=[strfulldesc],
                                    **extra_kwargs
                                )
                                print(f"{strkeyfieldname}: {lngentityid}, {strfulldesc} ({strlangcode}) -> UPDATED")
                            else:
                                chromacollection.add(
                                    ids=[strdocid],
                                    documents=[strfulldesc],
                                    **extra_kwargs
                                )
                                print(f"{strkeyfieldname}: {lngentityid}, {strfulldesc} ({strlangcode}) -> ADDED")

                print(f"Delete all {strentityname} embeddings that do not exist anymore in the {strtablename} table")
                f_logmemory(f"before {strentityname} cleanup")
                try:
                    lngcollectioncount = chromacollection.count()
                    print(f"{strentityname} collection holds {lngcollectioncount} docs")
                except Exception as exc:
                    print(f"Could not count {strentityname} collection: {exc}")
                batch_size = 1000
                offset = 0
                lngdeletedcount = 0
                lngnondeletedcount = 0
                while True:
                    try:
                        results = chromacollection.get(include=[], limit=batch_size, offset=offset)
                    except Exception as exc:
                        print(f"[CHROMA] get() failed on {strentityname} at offset {offset}: {exc}")
                        f_logmemory(f"at {strentityname} get() failure")
                        raise
                    ids = results["ids"]
                    if not ids:
                        break
                    for id in ids:
                        parts = id.split('_')
                        if len(parts) < 3:
                            continue
                        docentity = parts[0]
                        docid = parts[1]
                        doclang = parts[2]
                        if docentity != strentityname + "id":
                            continue
                        if id_is_numeric:
                            if not str(docid).isdigit():
                                continue
                            strsql = "SELECT " + strkeyfieldname + " FROM " + strtablename + " WHERE " + strkeyfieldname + " = " + docid + " "
                        else:
                            docid_sql = str(docid).replace("'", "''")
                            strsql = "SELECT " + strkeyfieldname + " FROM " + strtablename + " WHERE " + strkeyfieldname + " = '" + docid_sql + "' "
                        cursor.execute(strsql)
                        lngrowcount = cursor.rowcount
                        if lngrowcount == 0:
                            chromacollection.delete(ids=[id])
                            print(f"Deleted {id} ")
                            lngdeletedcount += 1
                        else:
                            print(f"Not deleted {id} ")
                            lngnondeletedcount += 1
                    if len(ids) < batch_size:
                        break
                    offset += batch_size
                print(f"Deleted {lngdeletedcount} {strentityname} docs")
                print(f"Not deleted {lngnondeletedcount} {strentityname} docs")
                cp.f_setservervariable(strservervariablenamedeletereport, f"Deleted {lngdeletedcount} {strentityname} docs (enabled)", "", 0)
                cp.f_setservervariable(strservervariablenamenotdeletereport, f"Not deleted {lngnondeletedcount} {strentityname} docs", "", 0)
                cp.f_setservervariable(strservervariablenameid, "", f"Current {strentityname} ID in the embedding update process", 0)
                cp.f_setservervariable(strservervariablenamestartdatetime, strprocessstartlocal, f"Date and time of the last start of the {strentityname} embedding update process", 0)

            def f_process_single_language_entity_embeddings(*, strentityname, strentitycollection, strtablename, strkeyfieldname, stroldid, strnamefield, chromacollection, doclang="en", print_sql=False, force_update_id_leq=None):
                """Sync single-language ChromaDB embeddings for an entity table.

                Queries the database for rows updated since the last run (or from ``stroldid``),
                then adds, updates, or deletes the corresponding ChromaDB document using a single
                name field. After processing updates, sweeps the collection and removes stale
                documents whose source row no longer exists in the database.

                Simpler counterpart to ``f_process_bilingual_t2s_entity_embeddings`` for
                entities that have only one language variant.

                Args:
                    strentityname: Short entity identifier used in doc IDs and server variables
                        (e.g. ``"award"``).
                    strentitycollection: Human-readable collection label for log messages.
                    strtablename: Source database table name.
                    strkeyfieldname: Primary-key column name in the source table.
                    stroldid: Resume from this ID value (empty string to start from the
                        beginning).
                    strnamefield: Column name containing the entity name/text to embed.
                    chromacollection: Target ChromaDB collection object.
                    doclang: Language code stored in the document ID and metadata (default
                        ``"en"``).
                    print_sql: When ``True``, prints the generated SQL query before executing.
                    force_update_id_leq: When set, forces a re-embedding for all entities with
                        ID ≤ this value by ignoring the cached document text during comparison.
                """
                print("Create embeddings for the " + strentitycollection)

                strservervariablenameid = strservervariableprefix + strentityname + "id"
                strservervariablenamestartdatetime = strservervariableprefix + strentityname + "startdatetime"
                strservervariablenamedeletereport = strservervariableprefix + strentityname + "deletereport"
                strservervariablenamenotdeletereport = strservervariableprefix + strentityname + "notdeletereport"

                strstartdatetimeprevious = cp.f_getservervariable(strservervariablenamestartdatetime, 0)
                strprocessstartlocal = datetime.now(cp.paris_tz).strftime("%Y-%m-%d %H:%M:%S")

                strsql = ""
                strsql += "SELECT " + strkeyfieldname + ", " + strnamefield + ", DELETED "
                strsql += "FROM " + strtablename + " "
                if stroldid != "":
                    strsql += "WHERE " + strkeyfieldname + " >= " + stroldid + " "
                if strstartdatetimeprevious is not None and str(strstartdatetimeprevious).strip() != "":
                    strstartdatetimeprevious = str(strstartdatetimeprevious).strip().replace("'", "''")
                    if stroldid != "":
                        strsql += "AND TIM_UPDATED >= '" + strstartdatetimeprevious + "' "
                    else:
                        strsql += "WHERE TIM_UPDATED >= '" + strstartdatetimeprevious + "' "
                strsql += "ORDER BY " + strkeyfieldname + " ASC "
                if print_sql:
                    print(strsql)
                try:
                    cursor.execute(strsql)
                except Exception:
                    strsql = ""
                    strsql += "SELECT " + strkeyfieldname + ", " + strnamefield + ", DELETED "
                    strsql += "FROM " + strtablename + " "
                    if stroldid != "":
                        strsql += "WHERE " + strkeyfieldname + " >= " + stroldid + " "
                    strsql += "ORDER BY " + strkeyfieldname + " ASC "
                    if print_sql:
                        print(strsql)
                    cursor.execute(strsql)

                lngrowcount = cursor.rowcount
                print(f"{lngrowcount} lines")
                results = cursor.fetchall()
                for row in results:
                    lngentityid = row[strkeyfieldname]
                    cp.f_setservervariable(strservervariablenameid, str(lngentityid), f"Current {strentityname} ID in the embedding update process", 0)
                    strname = (row.get(strnamefield) or "").strip()
                    if strname == "":
                        continue
                    intdeleted = row.get('DELETED', 0)
                    strdocid = strentityname + "id_" + str(lngentityid) + "_" + doclang
                    strfulldesc = strname
                    if len(strfulldesc) > max_chars:
                        strfulldesc = strfulldesc[:max_chars] + "..."
                    existing_doc = chromacollection.get(ids=[strdocid])
                    if existing_doc and len(existing_doc['ids']) > 0:
                        strdoctext = existing_doc['documents'][0]
                        if force_update_id_leq is not None and lngentityid <= force_update_id_leq:
                            strdoctext = ""
                        if strdoctext == strfulldesc:
                            continue
                    if intdeleted == 1:
                        if existing_doc and len(existing_doc['ids']) > 0:
                            chromacollection.delete(ids=[strdocid])
                            print(f"{strkeyfieldname}: {lngentityid}, {strfulldesc} -> DELETED")
                            continue
                    if existing_doc and len(existing_doc['ids']) > 0:
                        chromacollection.update(
                            ids=[strdocid],
                            documents=[strfulldesc]
                        )
                        print(f"{strkeyfieldname}: {lngentityid}, {strfulldesc} -> UPDATED")
                    else:
                        chromacollection.add(
                            ids=[strdocid],
                            documents=[strfulldesc]
                        )
                        print(f"{strkeyfieldname}: {lngentityid}, {strfulldesc} -> ADDED")

                print(f"Delete all {strentityname} embeddings that do not exist anymore in the {strtablename} table")
                f_logmemory(f"before {strentityname} cleanup")
                try:
                    lngcollectioncount = chromacollection.count()
                    print(f"{strentityname} collection holds {lngcollectioncount} docs")
                except Exception as exc:
                    print(f"Could not count {strentityname} collection: {exc}")
                batch_size = 1000
                offset = 0
                lngdeletedcount = 0
                lngnondeletedcount = 0
                while True:
                    try:
                        results = chromacollection.get(include=[], limit=batch_size, offset=offset)
                    except Exception as exc:
                        print(f"[CHROMA] get() failed on {strentityname} at offset {offset}: {exc}")
                        f_logmemory(f"at {strentityname} get() failure")
                        raise
                    ids = results["ids"]
                    if not ids:
                        break
                    for id in ids:
                        parts = id.split('_')
                        docentity = parts[0]
                        docid = parts[1]
                        doclang2 = parts[2]
                        if docentity != strentityname + "id":
                            continue
                        strsql = "SELECT " + strkeyfieldname + " FROM " + strtablename + " WHERE " + strkeyfieldname + " = " + docid + " "
                        cursor.execute(strsql)
                        lngrowcount = cursor.rowcount
                        if lngrowcount == 0:
                            chromacollection.delete(ids=[id])
                            print(f"Deleted {id} ")
                            lngdeletedcount += 1
                        else:
                            print(f"Not deleted {id} ")
                            lngnondeletedcount += 1
                    if len(ids) < batch_size:
                        break
                    offset += batch_size
                print(f"Deleted {lngdeletedcount} {strentityname} docs")
                print(f"Not deleted {lngnondeletedcount} {strentityname} docs")
                cp.f_setservervariable(strservervariablenamedeletereport, f"Deleted {lngdeletedcount} {strentityname} docs (enabled)", "", 0)
                cp.f_setservervariable(strservervariablenamenotdeletereport, f"Not deleted {lngnondeletedcount} {strentityname} docs", "", 0)
                cp.f_setservervariable(strservervariablenameid, "", f"Current {strentityname} ID in the embedding update process", 0)
                cp.f_setservervariable(strservervariablenamestartdatetime, strprocessstartlocal, f"Date and time of the last start of the {strentityname} embedding update process", 0)

            def f_composet2slocationdocument(strname, strtype, stroverview, lang_code):
                """Compose the document of one t2slocation in one language.

                ``<name>: <type word>, <Wikidata description>``; the parts after the colon are
                optional. The colon is the separator that fastapi-text2sql declares as
                ``document_name_separator`` so that only the name enters the lexical ratio,
                while the type and the description stay in the vector: they are what separates
                "Paris, capital and largest city of France" from "Paris, city in Texas", two
                documents that the bare label rendered strictly identical.
                """
                arrparts = []
                if strtype != "":
                    arrparts.append(ARR_T2SLOCATION_TYPE_LABEL.get(lang_code, {}).get(strtype, strtype))
                if stroverview != "":
                    arrparts.append(stroverview)
                strdocument = strname
                if arrparts:
                    strdocument += ": " + ", ".join(arrparts)
                if len(strdocument) > max_chars:
                    strdocument = strdocument[:max_chars] + "..."
                return strdocument

            def f_composet2ssourceworkdocument(strname, strtype, stroverview, lang_code, row):
                """Compose the document of one source work in one language.

                ``<name>: <form or type word>, <year>, <Wikidata description>``, the parts after the
                colon optional, the colon being the ``document_name_separator`` of fastapi-text2sql
                so that only the name enters the lexical ratio. The form or type and the year stay in
                the vector: they separate "Dracula: literary work, 1897" from "Dracula: film or
                series, 1931".
                """
                arrlabels = ARR_T2SSOURCEWORK_TYPE_LABEL.get(lang_code, {})
                strform = (row.get("SOURCE_WORK_FORM") or "").strip()
                arrparts = []
                strkind = arrlabels.get(strform, strform) if strform != "" else arrlabels.get(strtype, strtype)
                if strkind:
                    arrparts.append(strkind)
                if row.get("SOURCE_WORK_YEAR") is not None:
                    arrparts.append(str(row.get("SOURCE_WORK_YEAR")))
                if stroverview != "":
                    arrparts.append(stroverview)
                strdocument = strname
                if arrparts:
                    strdocument += ": " + ", ".join(arrparts)
                if len(strdocument) > max_chars:
                    strdocument = strdocument[:max_chars] + "..."
                return strdocument

            def f_process_t2slocation_embeddings(*, strentityname, strentitycollection, strtablename, stroldid, chromacollection,
                                                 strkeycol="ID_LOCATION", strnamecol="LOCATION_NAME",
                                                 strnamefrcol="LOCATION_NAME_FR", strtypecol="LOCATION_TYPE",
                                                 strtypemetakey="location_type", strextracols="", fcompose=None):
                """Sync the ``t2slocations`` collection with the ``T_WC_T2S_LOCATION`` read-model (EMBEDDING-UPDATE-005).

                Generalised on 2026-10-10 for ``t2ssourceworks`` (process 217, EMBEDDING-UPDATE-011):
                the key, name, French name and type columns, the metadata key of the type, extra
                SELECT columns and the document composer are parameters, their defaults being the
                location ones, so process 216 runs exactly as before.

                Same two watermarks and same closing server variables as the generic functions.
                Four differences, each decided on 2026-09-13 and explained next to the code: the
                document key is ``ID_LOCATION`` (stable since the process 72 fix of the same day, the
                Wikidata id travels in the metadata); the document carries ``LOCATION_TYPE`` and the
                Wikidata description; metadata is reconciled without re-embedding when only it
                changed; the orphan sweep is one set difference, not one SELECT per document.
                """
                print("Create embeddings for the " + strentitycollection)

                strservervariablenameid = strservervariableprefix + strentityname + "id"
                strservervariablenamestartdatetime = strservervariableprefix + strentityname + "startdatetime"
                strservervariablenamedeletereport = strservervariableprefix + strentityname + "deletereport"
                strservervariablenamenotdeletereport = strservervariableprefix + strentityname + "notdeletereport"

                strstartdatetimeprevious = cp.f_getservervariable(strservervariablenamestartdatetime, 0)
                strprocessstartlocal = datetime.now(cp.paris_tz).strftime("%Y-%m-%d %H:%M:%S")

                # LA CLE DU DOCUMENT EST ID_LOCATION, comme pour les autres entites T2S (awards,
                # deaths, nominations : l'entier de la table dans l'identifiant, le QID en
                # metadonnee). Le 2026-09-13, le processus 72 de tmdb-movie-preprocess renumerotait
                # encore ID_LOCATION a chaque reconstruction nocturne ; il a ete corrige le meme
                # jour (identifiant reporte par jointure, lieux sortis du perimetre conserves en
                # DELETED = 1, nouveaux numerotes au-dela du maximum). Cette collection ne doit
                # etre construite qu'APRES ce correctif : sur une table qui renumerote, chaque
                # nuit re-clerait et re-plongerait tout.
                if fcompose is None:
                    fcompose = lambda strname, strtype, stroverview, lang_code, row: f_composet2slocationdocument(strname, strtype, stroverview, lang_code)
                strsql = ""
                strsql += ("SELECT " + strkeycol + ", ID_WIKIDATA, " + strnamecol + ", " + strnamefrcol + ", OVERVIEW, "
                           + strtypecol + ", DELETED" + (", " + strextracols if strextracols else "") + " ")
                strsql += "FROM " + strtablename + " "
                strsql += "WHERE " + strkeycol + " IS NOT NULL "
                if stroldid is not None and str(stroldid).strip().isdigit():
                    strsql += "AND " + strkeycol + " >= " + str(int(str(stroldid).strip())) + " "
                if strstartdatetimeprevious is not None and str(strstartdatetimeprevious).strip() != "":
                    strsql += "AND TIM_UPDATED >= '" + str(strstartdatetimeprevious).strip().replace("'", "''") + "' "
                strsql += "ORDER BY " + strkeycol + " ASC "
                # Pas de rejeu sans le filtre de date en cas d'erreur : le 209 le faisait, et une
                # erreur quelconque basculait en silence d'un passage incremental a un balayage
                # complet. Ici l'erreur remonte.
                cursor.execute(strsql)
                results = cursor.fetchall()
                print(f"{len(results)} lines")

                arrmetadatakeys = ("id", "language", "name", "id_wikidata", strtypemetakey)
                lngbatchsize = 500
                lngaddedcount = 0
                lngupdatedcount = 0
                lngmetadatacount = 0
                lngremovedcount = 0
                lngunchangedcount = 0
                for lngoffset in range(0, len(results), lngbatchsize):
                    arrrows = results[lngoffset:lngoffset + lngbatchsize]
                    cp.f_setservervariable(strservervariablenameid, str(arrrows[0][strkeycol]), f"Current {strentityname} ID in the embedding update process", 0)
                    arrexpected = {}
                    arrremovecandidates = []
                    for row in arrrows:
                        strwikidataid = (row.get("ID_WIKIDATA") or "").strip()
                        lnglocationid = row.get(strkeycol)
                        intdeleted = row.get("DELETED") or 0
                        strtype = (row.get(strtypecol) or "").strip()
                        stroverview = (row.get("OVERVIEW") or "").strip().replace("\n", " ")
                        arrname = {}
                        arrname["en"] = (row.get(strnamecol) or "").strip()
                        arrname["fr"] = (row.get(strnamefrcol) or "").strip()
                        for lang_code in ("en", "fr"):
                            strdocid = strentityname + "id_" + str(lnglocationid) + "_" + lang_code
                            strname = arrname[lang_code]
                            # Le francais est saute quand son LIBELLE est le libelle anglais : la
                            # regle des autres collections, portee sur le nom et non sur le
                            # document entier, puisque le mot de type differe toujours entre les
                            # deux langues. Un document qui n'a plus lieu d'etre est retire.
                            if intdeleted == 1 or strname == "" or (lang_code == "fr" and strname == arrname["en"]):
                                arrremovecandidates.append(strdocid)
                                continue
                            strdocument = fcompose(strname, strtype, stroverview, lang_code, row)
                            arrmetadata = {"id": str(lnglocationid), "language": lang_code, "name": strname, "id_wikidata": strwikidataid}
                            if strtype != "":
                                arrmetadata[strtypemetakey] = strtype
                            arrexpected[strdocid] = (strdocument, arrmetadata)

                    # Un seul get par lot, la ou le 209 en faisait un par document.
                    arrexisting = {}
                    arrbatchids = list(arrexpected.keys()) + arrremovecandidates
                    if arrbatchids:
                        existing_docs = chromacollection.get(ids=arrbatchids, include=["documents", "metadatas"])
                        arrexistingdocuments = existing_docs.get("documents") or []
                        arrexistingmetadatas = existing_docs.get("metadatas") or []
                        for lngi, strexistingid in enumerate(existing_docs["ids"]):
                            strexistingdoc = arrexistingdocuments[lngi] if lngi < len(arrexistingdocuments) else None
                            arrexistingmetadata = arrexistingmetadatas[lngi] if lngi < len(arrexistingmetadatas) else None
                            arrexisting[strexistingid] = (strexistingdoc, arrexistingmetadata or {})

                    arrremoveids = [strdocid for strdocid in arrremovecandidates if strdocid in arrexisting]
                    if arrremoveids:
                        chromacollection.delete(ids=arrremoveids)
                        for strdocid in arrremoveids:
                            print(f"{strdocid} -> DELETED")
                        lngremovedcount += len(arrremoveids)

                    arraddids, arradddocuments, arraddmetadatas = [], [], []
                    arrupdateids, arrupdatedocuments, arrupdatemetadatas = [], [], []
                    arrmetadataids, arrmetadatametadatas = [], []
                    for strdocid, (strdocument, arrmetadata) in arrexpected.items():
                        if strdocid not in arrexisting:
                            arraddids.append(strdocid)
                            arradddocuments.append(strdocument)
                            arraddmetadatas.append(arrmetadata)
                            print(f"{strkeycol}: {arrmetadata['id']}, {strdocument} -> ADDED")
                            continue
                        strexistingdoc, arrexistingmetadata = arrexisting[strdocid]
                        if strexistingdoc != strdocument:
                            arrupdateids.append(strdocid)
                            arrupdatedocuments.append(strdocument)
                            arrupdatemetadatas.append(arrmetadata)
                            print(f"{strkeycol}: {arrmetadata['id']}, {strdocument} -> UPDATED")
                            continue
                        arrexistingmanaged = {strkey: strvalue for strkey, strvalue in arrexistingmetadata.items() if strkey in arrmetadatakeys}
                        if arrexistingmanaged != arrmetadata:
                            # Le texte n'a pas bouge, donc le vecteur non plus : metadonnees seules,
                            # sans re-plongement (le cas d'un item Wikidata fusionne, dont le QID
                            # change sans que le nom bouge).
                            arrmetadataids.append(strdocid)
                            arrmetadatametadatas.append(arrmetadata)
                            print(f"{strkeycol}: {arrmetadata['id']}, {strdocument} -> METADATA")
                            continue
                        lngunchangedcount += 1

                    if arraddids:
                        chromacollection.add(ids=arraddids, documents=arradddocuments, metadatas=arraddmetadatas)
                        lngaddedcount += len(arraddids)
                    if arrupdateids:
                        chromacollection.update(ids=arrupdateids, documents=arrupdatedocuments, metadatas=arrupdatemetadatas)
                        lngupdatedcount += len(arrupdateids)
                    if arrmetadataids:
                        chromacollection.update(ids=arrmetadataids, metadatas=arrmetadatametadatas)
                        lngmetadatacount += len(arrmetadataids)

                print(f"{strentityname}: {lngaddedcount} added, {lngupdatedcount} updated (re-embedded), {lngmetadatacount} metadata-only, {lngremovedcount} removed, {lngunchangedcount} unchanged")

                # Les orphelins : une difference d'ensembles entre les cles de la collection et les
                # lignes vivantes, la ou le 209 faisait un SELECT par document.
                print(f"Delete all {strentityname} embeddings that do not exist anymore in the {strtablename} table")
                f_logmemory(f"before {strentityname} cleanup")
                cursor.execute("SELECT " + strkeycol + " FROM " + strtablename + " WHERE " + strkeycol + " IS NOT NULL AND (DELETED IS NULL OR DELETED = 0)")
                arrlivingids = set(str(row.get(strkeycol)) for row in cursor.fetchall())
                try:
                    lngcollectioncount = chromacollection.count()
                    print(f"{strentityname} collection holds {lngcollectioncount} docs")
                except Exception as exc:
                    print(f"Could not count {strentityname} collection: {exc}")
                batch_size = 1000
                offset = 0
                arrorphanids = []
                lngnondeletedcount = 0
                while True:
                    try:
                        results = chromacollection.get(include=[], limit=batch_size, offset=offset)
                    except Exception as exc:
                        print(f"[CHROMA] get() failed on {strentityname} at offset {offset}: {exc}")
                        f_logmemory(f"at {strentityname} get() failure")
                        raise
                    ids = results["ids"]
                    if not ids:
                        break
                    for id in ids:
                        parts = id.split('_')
                        if len(parts) < 3:
                            continue
                        if parts[0] != strentityname + "id":
                            continue
                        if not str(parts[1]).isdigit():
                            continue
                        if parts[1] in arrlivingids:
                            lngnondeletedcount += 1
                        else:
                            arrorphanids.append(id)
                    if len(ids) < batch_size:
                        break
                    offset += batch_size
                # Supprimes APRES le balayage : supprimer pendant une pagination par offset decale
                # les pages et saute des documents.
                for lngoffset in range(0, len(arrorphanids), 500):
                    chromacollection.delete(ids=arrorphanids[lngoffset:lngoffset + 500])
                for id in arrorphanids:
                    print(f"Deleted {id} ")
                lngdeletedcount = len(arrorphanids)
                print(f"Deleted {lngdeletedcount} {strentityname} docs")
                print(f"Not deleted {lngnondeletedcount} {strentityname} docs")
                cp.f_setservervariable(strservervariablenamedeletereport, f"Deleted {lngdeletedcount} {strentityname} docs (enabled)", "", 0)
                cp.f_setservervariable(strservervariablenamenotdeletereport, f"Not deleted {lngnondeletedcount} {strentityname} docs", "", 0)
                cp.f_setservervariable(strservervariablenameid, "", f"Current {strentityname} ID in the embedding update process", 0)
                cp.f_setservervariable(strservervariablenamestartdatetime, strprocessstartlocal, f"Date and time of the last start of the {strentityname} embedding update process", 0)

            #arrprocessscope = {201: 'topic', 202: 'movie', 203: 'serie', 204: 'person', 205: 'company', 206: 'network', 207: 'character', 208: 'group', 209: 'location', 210: 'award'}
            arrprocessscope = {201: 'topic', 202: 'movie', 203: 'serie', 205: 'company', 206: 'network', 208: 'group', 210: 'award', 211: 'list', 212: 'collection', 213: 'movement', 214: 'death', 215: 'nomination', 216: 't2slocation', 217: 't2ssourcework'}
            strservervariablenametopicid = strservervariableprefix + "topic" + "id"
            strservervariablenamemovieid = strservervariableprefix + "movie" + "id"
            strservervariablenameserieid = strservervariableprefix + "serie" + "id"
            strservervariablenamepersonid = strservervariableprefix + "person" + "id"
            strservervariablenamecompanyid = strservervariableprefix + "company" + "id"
            strservervariablenamenetworkid = strservervariableprefix + "network" + "id"
            strservervariablenamecharacterid = strservervariableprefix + "character" + "id"
            strservervariablenamegroupid = strservervariableprefix + "group" + "id"
            strservervariablenamelocationid = strservervariableprefix + "location" + "id"
            strservervariablenameawardid = strservervariableprefix + "award" + "id"
            strservervariablenamelistid = strservervariableprefix + "list" + "id"
            strservervariablenamecollectionid = strservervariableprefix + "collection" + "id"
            strservervariablenamemovementid = strservervariableprefix + "movement" + "id"
            strservervariablenamedeathid = strservervariableprefix + "death" + "id"
            strservervariablenamenominationid = strservervariableprefix + "nomination" + "id"
            strservervariablenamet2slocationid = strservervariableprefix + "t2slocation" + "id"
            strtopicidold = cp.f_getservervariable(strservervariablenametopicid,0)
            strmovieidold = cp.f_getservervariable(strservervariablenamemovieid,0)
            strserieidold = cp.f_getservervariable(strservervariablenameserieid,0)
            strpersonidold = cp.f_getservervariable(strservervariablenamepersonid,0)
            strcompanyidold = cp.f_getservervariable(strservervariablenamecompanyid,0)
            strnetworkidold = cp.f_getservervariable(strservervariablenamenetworkid,0)
            strcharacteridold = cp.f_getservervariable(strservervariablenamecharacterid,0)
            strgroupidold = cp.f_getservervariable(strservervariablenamegroupid,0)
            strlocationidold = cp.f_getservervariable(strservervariablenamelocationid,0)
            strawardidold = cp.f_getservervariable(strservervariablenameawardid,0)
            strlistidold = cp.f_getservervariable(strservervariablenamelistid,0)
            strcollectionidold = cp.f_getservervariable(strservervariablenamecollectionid,0)
            strmovementidold = cp.f_getservervariable(strservervariablenamemovementid,0)
            strdeathidold = cp.f_getservervariable(strservervariablenamedeathid,0)
            strnominationidold = cp.f_getservervariable(strservervariablenamenominationid,0)
            strt2slocationidold = cp.f_getservervariable(strservervariablenamet2slocationid,0)
            strservervariablenamet2ssourceworkid = strservervariableprefix + "t2ssourcework" + "id"
            strt2ssourceworkidold = cp.f_getservervariable(strservervariablenamet2ssourceworkid,0)

            strcurrentcontent = cp.f_getservervariable(strservervariablenamecurrentcontent,0)
            
            if strcurrentcontent == "movie":
                arrprocessscope = {202: 'movie', 203: 'serie', 205: 'company', 206: 'network', 208: 'group', 210: 'award', 211: 'list', 212: 'collection', 213: 'movement', 214: 'death', 215: 'nomination', 216: 't2slocation', 217: 't2ssourcework'}
            elif strcurrentcontent == "serie":
                arrprocessscope = {203: 'serie', 205: 'company', 206: 'network', 208: 'group', 210: 'award', 211: 'list', 212: 'collection', 213: 'movement', 214: 'death', 215: 'nomination', 216: 't2slocation', 217: 't2ssourcework'}
            elif strcurrentcontent == "person":
                # Process 204 is retired: an old resume point inside it resumes at 205.
                arrprocessscope = {205: 'company', 206: 'network', 208: 'group', 210: 'award', 211: 'list', 212: 'collection', 213: 'movement', 214: 'death', 215: 'nomination', 216: 't2slocation', 217: 't2ssourcework'}
            elif strcurrentcontent == "company":
                arrprocessscope = {205: 'company', 206: 'network', 208: 'group', 210: 'award', 211: 'list', 212: 'collection', 213: 'movement', 214: 'death', 215: 'nomination', 216: 't2slocation', 217: 't2ssourcework'}
            elif strcurrentcontent == "network":
                arrprocessscope = {206: 'network', 208: 'group', 210: 'award', 211: 'list', 212: 'collection', 213: 'movement', 214: 'death', 215: 'nomination', 216: 't2slocation', 217: 't2ssourcework'}
            elif strcurrentcontent == "group":
                arrprocessscope = {208: 'group', 210: 'award', 211: 'list', 212: 'collection', 213: 'movement', 214: 'death', 215: 'nomination', 216: 't2slocation', 217: 't2ssourcework'}
            elif strcurrentcontent == "location":
                # Process 209 is retired (EMBEDDING-UPDATE-010): an old resume point inside it resumes at 210.
                arrprocessscope = {210: 'award', 211: 'list', 212: 'collection', 213: 'movement', 214: 'death', 215: 'nomination', 216: 't2slocation', 217: 't2ssourcework'}
            elif strcurrentcontent == "award":
                arrprocessscope = {210: 'award', 211: 'list', 212: 'collection', 213: 'movement', 214: 'death', 215: 'nomination', 216: 't2slocation', 217: 't2ssourcework'}
            elif strcurrentcontent == "list":
                arrprocessscope = {211: 'list', 212: 'collection', 213: 'movement', 214: 'death', 215: 'nomination', 216: 't2slocation', 217: 't2ssourcework'}
            elif strcurrentcontent == "collection":
                arrprocessscope = {212: 'collection', 213: 'movement', 214: 'death', 215: 'nomination', 216: 't2slocation', 217: 't2ssourcework'}
            elif strcurrentcontent == "movement":
                arrprocessscope = {213: 'movement', 214: 'death', 215: 'nomination', 216: 't2slocation', 217: 't2ssourcework'}
            elif strcurrentcontent == "death":
                arrprocessscope = {214: 'death', 215: 'nomination', 216: 't2slocation', 217: 't2ssourcework'}
            elif strcurrentcontent == "nomination":
                arrprocessscope = {215: 'nomination', 216: 't2slocation', 217: 't2ssourcework'}
            elif strcurrentcontent == "t2slocation":
                arrprocessscope = {216: 't2slocation', 217: 't2ssourcework'}
            elif strcurrentcontent == "t2ssourcework":
                arrprocessscope = {217: 't2ssourcework'}
            """
            elif strcurrentcontent == "character":
                arrprocessscope = {207: 'character', 208: 'group', 209: 'location'}
            """
            """ """
            if strprocessstart.startswith('2026-03-29'):
                # Testing nomination embeddings update
                arrprocessscope = {215: 'nomination'}
            """ """
            """
            # Fix to delete all movies with id like serieid* 
            print("Fix to delete all movies with id like serieid*")
            batch_size = 1000
            offset = 0
            while True:
                # Step 1: get all ids matching seriedb*
                results = movies.get(include=[], limit=batch_size, offset=offset)
                ids = results["ids"]
                #print(results["ids"])
                if not ids:
                    break
                ids_to_delete = [r for r in ids if r.startswith("serieid")]
                print("offset", offset, "ids_to_delete", ids_to_delete)
                if ids_to_delete:
                    movies.delete(ids=ids_to_delete)
                    print(f"Deleted {len(ids_to_delete)} docs with prefix 'serieid'")

                if len(ids) < batch_size:
                    break
                offset += batch_size
            """
            for intindex, strcontent in arrprocessscope.items():
                strcurrentprocess = f"{intindex}: processing " + strcontent + " embedding update"
                strprocessesexecuted += str(intindex) + ", "
                cp.f_setservervariable(strservervariablenameprocessesexecuted,strprocessesexecuted,strprocessesexecuteddesc,0)
                cp.f_setservervariable(strservervariablenamecurrentcontent,strcontent,"Current content processed in the embedding update process",0)
                if intindex == 201:
                    # Create embeddings for the topics
                    strentityname = "topic"
                    strentitycollection = "topics"
                    strtablename = "T_WC_T2S_TOPIC"
                    strkeyfieldname = "ID_TOPIC"
                    def f_topic_should_delete_row(row):
                        """Return True if the topic embedding should be deleted.

                        A topic with a combined movie+serie count of 1 or less is not
                        considered meaningful and its embedding is removed from the collection.
                        """
                        lngmoviecount = row.get('MOVIE_COUNT', 0) or 0
                        lngseriecount = row.get('SERIE_COUNT', 0) or 0
                        return (lngmoviecount + lngseriecount) <= 1

                    f_process_bilingual_t2s_entity_embeddings(
                        strentityname=strentityname,
                        strentitycollection=strentitycollection,
                        strtablename=strtablename,
                        strkeyfieldname=strkeyfieldname,
                        stroldid=strtopicidold,
                        strtitlefielden="TOPIC_NAME",
                        strtitlefieldfr="TOPIC_NAME_FR",
                        chromacollection=topics,
                        stridrecordfield="ID_RECORD",
                        extra_select_fields=["TOPIC_TYPE", "MOVIE_COUNT", "SERIE_COUNT"],
                        should_delete_row=f_topic_should_delete_row,
                        id_is_numeric=True,
                        overview_field="OVERVIEW",
                    )
                elif intindex == 202:
                    # Create embeddings for the movies
                    strentityname = "movie"
                    strentitycollection = "movies"
                    strtablename = "T_WC_T2S_MOVIE"
                    strtablelang = "T_WC_TMDB_MOVIE_LANG"
                    strkeyfieldname = "ID_MOVIE"
                    f_process_en_fr_original_title_embeddings_from_lang_table(
                        strentityname=strentityname,
                        strentitycollection=strentitycollection,
                        strtablename=strtablename,
                        strtablelang=strtablelang,
                        strkeyfieldname=strkeyfieldname,
                        stroldid=strmovieidold,
                        chromacollection=movies,
                        strtitlefielden="MOVIE_TITLE",
                        strtitlefieldfr="TITLE",
                        stroriginal_language_field="ORIGINAL_LANGUAGE",
                        stroriginal_title_field="ORIGINAL_TITLE",
                        stryearfield="RELEASE_YEAR",
                        id_is_numeric=True,
                    )
                elif intindex == 203:
                    # Create embeddings for the series
                    strentityname = "serie"
                    strentitycollection = "series"
                    strtablename = "T_WC_T2S_SERIE"
                    strtablelang = "T_WC_TMDB_SERIE_LANG"
                    strkeyfieldname = "ID_SERIE"
                    f_process_en_fr_original_title_embeddings_from_lang_table(
                        strentityname=strentityname,
                        strentitycollection=strentitycollection,
                        strtablename=strtablename,
                        strtablelang=strtablelang,
                        strkeyfieldname=strkeyfieldname,
                        stroldid=strserieidold,
                        chromacollection=series,
                        strtitlefielden="SERIE_TITLE",
                        strtitlefieldfr="TITLE",
                        stroriginal_language_field="ORIGINAL_LANGUAGE",
                        stroriginal_title_field="ORIGINAL_TITLE",
                        id_is_numeric=True,
                    )
                elif intindex == 205:
                    # Create embeddings for the companies
                    strentityname = "company"
                    strentitycollection = "companies"
                    strtablename = "T_WC_T2S_COMPANY"
                    strkeyfieldname = "ID_COMPANY"
                    f_process_single_language_entity_embeddings(
                        strentityname=strentityname,
                        strentitycollection=strentitycollection,
                        strtablename=strtablename,
                        strkeyfieldname=strkeyfieldname,
                        stroldid=strcompanyidold,
                        strnamefield="COMPANY_NAME",
                        chromacollection=companies,
                        doclang="en",
                        print_sql=True,
                        force_update_id_leq=60,
                    )
                elif intindex == 206:
                    # Create embeddings for the networks
                    strentityname = "network"
                    strentitycollection = "networks"
                    strtablename = "T_WC_T2S_NETWORK"
                    strkeyfieldname = "ID_NETWORK"
                    f_process_single_language_entity_embeddings(
                        strentityname=strentityname,
                        strentitycollection=strentitycollection,
                        strtablename=strtablename,
                        strkeyfieldname=strkeyfieldname,
                        stroldid=strnetworkidold,
                        strnamefield="NETWORK_NAME",
                        chromacollection=networks,
                        doclang="en",
                    )
                elif intindex == 1207:
                    # Create embeddings for the characters
                    # But define some stuff first:
                    # What is the ID for a character?
                    # Write the SQL query to get the characters
                    strentityname = "character"
                    strentitycollection = "characters"
                    strtablename = "T_WC_T2S_CHARACTER"
                    strkeyfieldname = "ID_CHARACTER"
                    f_process_single_language_entity_embeddings(
                        strentityname=strentityname,
                        strentitycollection=strentitycollection,
                        strtablename=strtablename,
                        strkeyfieldname=strkeyfieldname,
                        stroldid=strcharacteridold,
                        strnamefield="CHARACTER_NAME",
                        chromacollection=characters,
                        doclang="en",
                    )
                elif intindex == 208:
                    # Create embeddings for the groups
                    strentityname = "group"
                    strentitycollection = "groups"
                    strtablename = "T_WC_T2S_GROUP"
                    strkeyfieldname = "ID_GROUP"
                    f_process_bilingual_t2s_entity_embeddings(
                        strentityname=strentityname,
                        strentitycollection=strentitycollection,
                        strtablename=strtablename,
                        strkeyfieldname=strkeyfieldname,
                        stroldid=strgroupidold,
                        strtitlefielden="GROUP_NAME",
                        strtitlefieldfr="GROUP_NAME_FR",
                        chromacollection=groups,
                        stridrecordfield=None,
                        extra_metadata_fields={"id_wikidata": "ID_WIKIDATA"},
                        id_is_numeric=False,
                        overview_field=None,
                    )
                elif intindex == 210:
                    # Create embeddings for the awards
                    strentityname = "award"
                    strentitycollection = "awards"
                    strtablename = "T_WC_T2S_AWARD"
                    strkeyfieldname = "ID_AWARD"
                    f_process_bilingual_t2s_entity_embeddings(
                        strentityname=strentityname,
                        strentitycollection=strentitycollection,
                        strtablename=strtablename,
                        strkeyfieldname=strkeyfieldname,
                        stroldid=strawardidold,
                        strtitlefielden="AWARD_NAME",
                        strtitlefieldfr="AWARD_NAME_FR",
                        chromacollection=awards,
                        stridrecordfield=None,
                        extra_metadata_fields={"id_wikidata": "ID_WIKIDATA"},
                    )
                elif intindex == 211:
                    # Create embeddings for the lists
                    strentityname = "list"
                    strentitycollection = "lists"
                    strtablename = "T_WC_T2S_LIST"
                    strkeyfieldname = "ID_T2S_LIST"
                    f_process_bilingual_t2s_entity_embeddings(
                        strentityname=strentityname,
                        strentitycollection=strentitycollection,
                        strtablename=strtablename,
                        strkeyfieldname=strkeyfieldname,
                        stroldid=strlistidold,
                        strtitlefielden="LIST_NAME",
                        strtitlefieldfr="LIST_NAME_FR",
                        # Le nom seul, sans la description, comme pour les groupes.
                        # Mesure du 2026-08-29 : sur toute la table, QUATRE lignes portent un
                        # OVERVIEW, long de 105 caracteres en moyenne et valant 2,7 fois le nom.
                        # Une description de ce rapport ecrase le score lexical du garde de
                        # resolution, qui compare le nom tape au document entier : c'est le
                        # defaut trouve sur les collections (fastapi-text2sql -224), ou
                        # « flamenco trilogy » notait 20 contre un seuil de 72 face au document
                        # complet, et 80 face au nom seul.
                        # L'autre remede etait de declarer `document_name_separator` cote API,
                        # qui garde la description dans l'espace vectoriel et l'exclut du score.
                        # Il a ete ecarte ici : quatre lignes ne valent pas un mecanisme qui
                        # doit rester d'accord entre deux depots, accord qui a justement derive
                        # deux mois sans que personne ne puisse le voir.
                        overview_field=None,
                        chromacollection=lists,
                    )
                elif intindex == 212:
                    # Create embeddings for the collections
                    strentityname = "collection"
                    strentitycollection = "collections"
                    strtablename = "T_WC_T2S_COLLECTION"
                    strkeyfieldname = "ID_T2S_COLLECTION"
                    f_process_bilingual_t2s_entity_embeddings(
                        strentityname=strentityname,
                        strentitycollection=strentitycollection,
                        strtablename=strtablename,
                        strkeyfieldname=strkeyfieldname,
                        stroldid=strcollectionidold,
                        strtitlefielden="COLLECTION_NAME",
                        strtitlefieldfr="COLLECTION_NAME_FR",
                        chromacollection=collections,
                    )
                elif intindex == 213:
                    # Create embeddings for the movements
                    strentityname = "movement"
                    strentitycollection = "movements"
                    strtablename = "T_WC_T2S_MOVEMENT"
                    strkeyfieldname = "ID_MOVEMENT"
                    f_process_bilingual_t2s_entity_embeddings(
                        strentityname=strentityname,
                        strentitycollection=strentitycollection,
                        strtablename=strtablename,
                        strkeyfieldname=strkeyfieldname,
                        stroldid=strmovementidold,
                        strtitlefielden="MOVEMENT_NAME",
                        strtitlefieldfr="MOVEMENT_NAME_FR",
                        chromacollection=movements,
                    )
                elif intindex == 214:
                    # Create embeddings for the deaths
                    strentityname = "death"
                    strentitycollection = "deaths"
                    strtablename = "T_WC_T2S_DEATH"
                    strkeyfieldname = "ID_DEATH"
                    f_process_bilingual_t2s_entity_embeddings(
                        strentityname=strentityname,
                        strentitycollection=strentitycollection,
                        strtablename=strtablename,
                        strkeyfieldname=strkeyfieldname,
                        stroldid=strdeathidold,
                        strtitlefielden="DEATH_NAME",
                        strtitlefieldfr="DEATH_NAME_FR",
                        chromacollection=deaths,
                        stridrecordfield=None,
                        extra_metadata_fields={"id_wikidata": "ID_WIKIDATA"},
                        id_is_numeric=True,
                        overview_field="OVERVIEW",
                    )

                elif intindex == 215:
                    # Create embeddings for the nominations
                    strentityname = "nomination"
                    strentitycollection = "nominations"
                    strtablename = "T_WC_T2S_NOMINATION"
                    strkeyfieldname = "ID_NOMINATION"
                    f_process_bilingual_t2s_entity_embeddings(
                        strentityname=strentityname,
                        strentitycollection=strentitycollection,
                        strtablename=strtablename,
                        strkeyfieldname=strkeyfieldname,
                        stroldid=strnominationidold,
                        strtitlefielden="NOMINATION_NAME",
                        strtitlefieldfr="NOMINATION_NAME_FR",
                        chromacollection=nominations,
                        stridrecordfield=None,
                        extra_metadata_fields={"id_wikidata": "ID_WIKIDATA"},
                        id_is_numeric=True,
                        overview_field="OVERVIEW",
                    )

                elif intindex == 216:
                    # Create embeddings for the locations read-model (EMBEDDING-UPDATE-005)
                    strentityname = "t2slocation"
                    strentitycollection = "t2slocations"
                    strtablename = "T_WC_T2S_LOCATION"
                    if t2slocations is None:
                        print("t2slocations collection unavailable at startup, process 216 skipped this run.")
                    else:
                        f_process_t2slocation_embeddings(
                            strentityname=strentityname,
                            strentitycollection=strentitycollection,
                            strtablename=strtablename,
                            stroldid=strt2slocationidold,
                            chromacollection=t2slocations,
                        )

                elif intindex == 217:
                    # Create embeddings for the source works read-model (EMBEDDING-UPDATE-011):
                    # the works movies and series are based on, typed by process 73 of
                    # tmdb-movie-preprocess. Same function as 216, other columns.
                    strentityname = "t2ssourcework"
                    strentitycollection = "t2ssourceworks"
                    strtablename = "T_WC_T2S_SOURCE_WORK"
                    if t2ssourceworks is None:
                        print("t2ssourceworks collection unavailable at startup, process 217 skipped this run.")
                    else:
                        f_process_t2slocation_embeddings(
                            strentityname=strentityname,
                            strentitycollection=strentitycollection,
                            strtablename=strtablename,
                            stroldid=strt2ssourceworkidold,
                            chromacollection=t2ssourceworks,
                            strkeycol="ID_SOURCE_WORK",
                            strnamecol="SOURCE_WORK_NAME",
                            strnamefrcol="SOURCE_WORK_NAME_FR",
                            strtypecol="SOURCE_WORK_TYPE",
                            strtypemetakey="source_work_type",
                            strextracols="SOURCE_WORK_FORM, SOURCE_WORK_YEAR",
                            fcompose=f_composet2ssourceworkdocument,
                        )

                if intindex == 217:
                    # Last process is finished
                    cp.f_setservervariable(strservervariablenamecurrentcontent,"","Current content processed in the embedding update process",0)
            # Calculate total runtime and convert to readable format
            end_time = time.time()
            strtotalruntime = int(end_time - start_time)  # Total runtime in seconds
            readable_duration = cp.convert_seconds_to_duration(strtotalruntime)
            cp.f_setservervariable(strservervariablenametotalruntime,readable_duration,strtotalruntimedesc,0)
            print(f"Total runtime: {strtotalruntime} seconds ({readable_duration})")
except pymysql.MySQLError as e:
    print(f"❌ MySQL Error: {e}")
    conn = getattr(cp, "connectioncp", None)
    if conn is not None and getattr(conn, "open", False):
        conn.rollback()
