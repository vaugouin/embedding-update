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
    for name in [
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
}

topics = CHROMADB_COLLECTIONS_BY_NAME["topics"]
movies = CHROMADB_COLLECTIONS_BY_NAME["movies"]
series = CHROMADB_COLLECTIONS_BY_NAME["series"]
persons = CHROMADB_COLLECTIONS_BY_NAME["persons"]
companies = CHROMADB_COLLECTIONS_BY_NAME["companies"]
networks = CHROMADB_COLLECTIONS_BY_NAME["networks"]
characters = CHROMADB_COLLECTIONS_BY_NAME["characters"]
groups = CHROMADB_COLLECTIONS_BY_NAME["groups"]
locations = CHROMADB_COLLECTIONS_BY_NAME["locations"]
lists = CHROMADB_COLLECTIONS_BY_NAME["lists"]
collections = CHROMADB_COLLECTIONS_BY_NAME["collections"]
deaths = CHROMADB_COLLECTIONS_BY_NAME["deaths"]
awards = CHROMADB_COLLECTIONS_BY_NAME["awards"]
nominations = CHROMADB_COLLECTIONS_BY_NAME["nominations"]
movements = CHROMADB_COLLECTIONS_BY_NAME["movements"]

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

            #arrprocessscope = {201: 'topic', 202: 'movie', 203: 'serie', 204: 'person', 205: 'company', 206: 'network', 207: 'character', 208: 'group', 209: 'location', 210: 'award'}
            arrprocessscope = {201: 'topic', 202: 'movie', 203: 'serie', 204: 'person', 205: 'company', 206: 'network', 208: 'group', 209: 'location', 210: 'award', 211: 'list', 212: 'collection', 213: 'movement', 214: 'death', 215: 'nomination'}
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

            strcurrentcontent = cp.f_getservervariable(strservervariablenamecurrentcontent,0)
            
            if strcurrentcontent == "movie":
                arrprocessscope = {202: 'movie', 203: 'serie', 204: 'person', 205: 'company', 206: 'network', 208: 'group', 209: 'location', 210: 'award', 211: 'list', 212: 'collection', 213: 'movement', 214: 'death', 215: 'nomination'}
            elif strcurrentcontent == "serie":
                arrprocessscope = {203: 'serie', 204: 'person', 205: 'company', 206: 'network', 208: 'group', 209: 'location', 210: 'award', 211: 'list', 212: 'collection', 213: 'movement', 214: 'death', 215: 'nomination'}
            elif strcurrentcontent == "person":
                arrprocessscope = {204: 'person', 205: 'company', 206: 'network', 208: 'group', 209: 'location', 210: 'award', 211: 'list', 212: 'collection', 213: 'movement', 214: 'death', 215: 'nomination'}
            elif strcurrentcontent == "company":
                arrprocessscope = {205: 'company', 206: 'network', 208: 'group', 209: 'location', 210: 'award', 211: 'list', 212: 'collection', 213: 'movement', 214: 'death', 215: 'nomination'}
            elif strcurrentcontent == "network":
                arrprocessscope = {206: 'network', 208: 'group', 209: 'location', 210: 'award', 211: 'list', 212: 'collection', 213: 'movement', 214: 'death', 215: 'nomination'}
            elif strcurrentcontent == "group":
                arrprocessscope = {208: 'group', 209: 'location', 210: 'award', 211: 'list', 212: 'collection', 213: 'movement', 214: 'death', 215: 'nomination'}
            elif strcurrentcontent == "location":
                arrprocessscope = {209: 'location', 210: 'award', 211: 'list', 212: 'collection', 213: 'movement', 214: 'death', 215: 'nomination'}
            elif strcurrentcontent == "award":
                arrprocessscope = {210: 'award', 211: 'list', 212: 'collection', 213: 'movement', 214: 'death', 215: 'nomination'}
            elif strcurrentcontent == "list":
                arrprocessscope = {211: 'list', 212: 'collection', 213: 'movement', 214: 'death', 215: 'nomination'}
            elif strcurrentcontent == "collection":
                arrprocessscope = {212: 'collection', 213: 'movement', 214: 'death', 215: 'nomination'}
            elif strcurrentcontent == "movement":
                arrprocessscope = {213: 'movement', 214: 'death', 215: 'nomination'}
            elif strcurrentcontent == "death":
                arrprocessscope = {214: 'death', 215: 'nomination'}
            elif strcurrentcontent == "nomination":
                arrprocessscope = {215: 'nomination'}
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
                elif intindex == 204:
                    # Create embeddings for the persons
                    strentityname = "person"
                    strentitycollection = "persons"
                    strtablename = "T_WC_T2S_PERSON"
                    strkeyfieldname = "ID_PERSON"
                    f_process_single_language_entity_embeddings(
                        strentityname=strentityname,
                        strentitycollection=strentitycollection,
                        strtablename=strtablename,
                        strkeyfieldname=strkeyfieldname,
                        stroldid=strpersonidold,
                        strnamefield="PERSON_NAME",
                        chromacollection=persons,
                        doclang="en",
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
                elif intindex == 209:
                    # Create embeddings for the locations (narrative location, filming location)
                    strentityname = "location"
                    strentitycollection = "locations"
                    strtablename = "T_WC_T2S_ITEM"
                    strtablenameproperty = "T_WC_WIKIDATA_ITEM_PROPERTY"
                    strkeyfieldname = "ID_ITEM"
                    strkeyfieldnamet2s = "ID_WIKIDATA"
                    print("Create embeddings for the " + strentitycollection)

                    strservervariablenameid = strservervariableprefix + strentityname + "id"
                    strservervariablenamestartdatetime = strservervariableprefix + strentityname + "startdatetime"
                    strservervariablenamedeletereport = strservervariableprefix + strentityname + "deletereport"
                    strservervariablenamenotdeletereport = strservervariableprefix + strentityname + "notdeletereport"

                    strlocationstartdatetimeprevious = cp.f_getservervariable(strservervariablenamestartdatetime,0)
                    strprocessstart = datetime.now(cp.paris_tz).strftime("%Y-%m-%d %H:%M:%S")

                    strsql = ""
                    strsql += "SELECT DISTINCT " + strtablenameproperty + "." + strkeyfieldname + ", 'en' AS ENGLISH_LANGUAGE, t2s.ITEM_LABEL, 'fr' AS FRENCH_LANGUAGE, t2s.ITEM_LABEL_FR, t2s.DELETED "
                    strsql += "FROM " + strtablenameproperty + " "
                    strsql += "INNER JOIN " + strtablename + " t2s ON " + strtablenameproperty + "." + strkeyfieldname + " = t2s." + strkeyfieldnamet2s + " "
                    strsql += "WHERE " + strtablenameproperty + ".ID_PROPERTY IN ('P840', 'P915') "
                    if strlocationidold != "":
                        strsql += "AND " + strtablenameproperty + "." + strkeyfieldname + " >= '" + strlocationidold + "' "
                    if strlocationstartdatetimeprevious is not None and str(strlocationstartdatetimeprevious).strip() != "":
                        strlocationstartdatetimeprevious = str(strlocationstartdatetimeprevious).strip().replace("'", "''")
                        strsql += "AND t2s.TIM_UPDATED >= '" + strlocationstartdatetimeprevious + "' "
                    strsql += "ORDER BY " + strtablenameproperty + "." + strkeyfieldname + " ASC "
                    try:
                        cursor.execute(strsql)
                    except Exception:
                        strsql = ""
                        strsql += "SELECT DISTINCT " + strtablenameproperty + "." + strkeyfieldname + ", 'en' AS ENGLISH_LANGUAGE, t2s.ITEM_LABEL, 'fr' AS FRENCH_LANGUAGE, t2s.ITEM_LABEL_FR, t2s.DELETED "
                        strsql += "FROM " + strtablenameproperty + " "
                        strsql += "INNER JOIN " + strtablename + " t2s ON " + strtablenameproperty + "." + strkeyfieldname + " = t2s." + strkeyfieldnamet2s + " "
                        strsql += "WHERE " + strtablenameproperty + ".ID_PROPERTY IN ('P840', 'P915') "
                        if strlocationidold != "":
                            strsql += "AND " + strtablenameproperty + "." + strkeyfieldname + " >= '" + strlocationidold + "' "
                        strsql += "ORDER BY " + strtablenameproperty + "." + strkeyfieldname + " ASC "
                        cursor.execute(strsql)
                    lngrowcount = cursor.rowcount
                    print(f"{lngrowcount} lines")
                    results = cursor.fetchall()
                    for row in results:
                        strlocationid = row[strkeyfieldname]
                        cp.f_setservervariable(strservervariablenameid,strlocationid,f"Current {strentityname} ID in the embedding update process",0)
                        arrlanguage = {}
                        arrtitle = {}
                        arrlanguage['en'] = (row.get('ENGLISH_LANGUAGE') or '').strip()
                        arrtitle['en'] = (row.get('ITEM_LABEL') or '').strip()
                        arrlanguage['fr'] = (row.get('FRENCH_LANGUAGE') or '').strip()
                        arrtitle['fr'] = (row.get('ITEM_LABEL_FR') or '').strip()
                        intdeleted = row.get('DELETED', 0)
                        # Process embeddings for each title in each language
                        strfirstlangfulldesc = None
                        for lang_code in arrlanguage.keys():
                            if lang_code in arrtitle and arrtitle[lang_code].strip() != "":
                                strdocid = strentityname + "id_" + strlocationid + "_" + lang_code
                                strlocationfulldesc = arrtitle[lang_code]
                                if len(strlocationfulldesc) > max_chars:
                                    strlocationfulldesc = strlocationfulldesc[:max_chars] + "..."
                                if strfirstlangfulldesc is None:
                                    strfirstlangfulldesc = strlocationfulldesc
                                elif strlocationfulldesc == strfirstlangfulldesc:
                                    continue
                                print(strlocationfulldesc)
                                # Check if the document exists in ChromaDB
                                existing_doc = locations.get(ids=[strdocid])

                                if intdeleted == 1:
                                    # This document is deleted
                                    # Delete it from the collection
                                    locations.delete(ids=[strdocid])
                                    print(f"{strkeyfieldname}: {strlocationid}, {strlocationfulldesc} -> DELETED")
                                    continue
                                
                                if existing_doc and len(existing_doc['ids']) > 0:
                                    strdoctext = existing_doc['documents'][0]
                                    if strdoctext == strlocationfulldesc:
                                        # This document was already processed to an embedding
                                        # Nothing to do 
                                        #print(f"{strkeyfieldname}: {strlocationid}, {strlocationfulldesc} -> ALREADY PROCESSED")
                                        continue
                                
                                # Check if the document exists in ChromaDB
                                if existing_doc and len(existing_doc['ids']) > 0:
                                    locations.update(
                                        ids=[strdocid],
                                        documents=[strlocationfulldesc],
                                        metadatas=[{"id": strlocationid, "language": lang_code}]                                        
                                    )
                                    print(f"{strkeyfieldname}: {strlocationid}, {strlocationfulldesc} -> UPDATED")
                                else:
                                    # Add it to the collection
                                    locations.add(
                                        ids=[strdocid],
                                        documents=[strlocationfulldesc],
                                        metadatas=[{"id": strlocationid, "language": lang_code}]                                        
                                )
                                print(f"{strkeyfieldname}: {strlocationid}, {strlocationfulldesc} -> ADDED")

                    # Now delete all location embeddings that do not exist anymore in the T2S_ITEM table
                    print(f"Delete all {strentityname} embeddings that do not exist anymore in the {strtablename} table")
                    batch_size = 1000
                    offset = 0
                    lngdeletedcount = 0
                    lngnondeletedcount = 0
                    while True:
                        # Step 1: get all ids from locations
                        results = locations.get(include=[], limit=batch_size, offset=offset)
                        ids = results["ids"]
                        #print(results["ids"])
                        if not ids:
                            break
                        for id in ids:
                            # Extract the 3 parts from id using underscore separator
                            parts = id.split('_')
                            docentity = parts[0]
                            docid = parts[1]
                            doclang = parts[2]
                            if docentity != strentityname + "id":
                                continue
                            strsql = "SELECT " + strkeyfieldnamet2s + " FROM " + strtablename + " WHERE " + strkeyfieldnamet2s + " = '" + docid + "' "
                            #print(strsql)
                            cursor.execute(strsql)
                            lngrowcount = cursor.rowcount
                            if lngrowcount == 0:
                                locations.delete(ids=[id])
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
                    cp.f_setservervariable(strservervariablenamedeletereport,f"Deleted {lngdeletedcount} {strentityname} docs (enabled)","",0)
                    cp.f_setservervariable(strservervariablenamenotdeletereport,f"Not deleted {lngnondeletedcount} {strentityname} docs","",0)
                    cp.f_setservervariable(strservervariablenameid,"",f"Current {strentityname} ID in the embedding update process",0)
                    cp.f_setservervariable(strservervariablenamestartdatetime,strprocessstart,f"Date and time of the last start of the {strentityname} embedding update process",0)

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

                if intindex == 215:
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
