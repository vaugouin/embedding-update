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

# Load environment variables from .env file
load_dotenv()

# Set your OpenAI API key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

# Validate that the API key was loaded
if not openai.api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables. Please check your .env file.")

class OpenAIEmbeddingFunction:
    def __init__(self, model="text-embedding-3-large"):
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

# Create or load a collection with the custom embedding function
strentitycollection = "topics"
topics = chroma_client.get_or_create_collection(
    name=strentitycollection,
    embedding_function=embedding_function  # Custom embedding model
)
strentitycollection = "movies"
movies = chroma_client.get_or_create_collection(
    name=strentitycollection,
    embedding_function=embedding_function  # Custom embedding model
)
strentitycollection = "series"
series = chroma_client.get_or_create_collection(
    name=strentitycollection,
    embedding_function=embedding_function  # Custom embedding model
)
strentitycollection = "persons"
persons = chroma_client.get_or_create_collection(
    name=strentitycollection,
    embedding_function=embedding_function  # Custom embedding model
)
strentitycollection = "companies"
companies = chroma_client.get_or_create_collection(
    name=strentitycollection,
    embedding_function=embedding_function  # Custom embedding model
)
strentitycollection = "networks"
networks = chroma_client.get_or_create_collection(
    name=strentitycollection,
    embedding_function=embedding_function  # Custom embedding model
)
strentitycollection = "characters"
characters = chroma_client.get_or_create_collection(
    name=strentitycollection,
    embedding_function=embedding_function  # Custom embedding model
)
strentitycollection = "groups"
groups = chroma_client.get_or_create_collection(
    name=strentitycollection,
    embedding_function=embedding_function  # Custom embedding model
)
strentitycollection = "locations"
locations = chroma_client.get_or_create_collection(
    name=strentitycollection,
    embedding_function=embedding_function  # Custom embedding model
)

#Anonymized queries collection
anonymizedqueries = chroma_client.get_or_create_collection(
    name="anonymizedqueries",
    embedding_function=embedding_function  # Custom embedding model
)

try:
    with cp.connectioncp:
        with cp.connectioncp.cursor() as cursor:
            cursor2 = cp.connectioncp.cursor()
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
            strtotalruntime = ""
            cp.f_setservervariable(strservervariablenametotalruntime,strtotalruntime,strtotalruntimedesc,0)
            
            # Ensure text length is within text-embedding-3-large model limits (8191 tokens)
            # Approximate 4 characters per token, so limit to ~32,000 characters to be safe
            max_chars = 32000

            #arrprocessscope = {201: 'topic', 202: 'movie', 203: 'serie', 204: 'person', 205: 'company', 206: 'network', 207: 'character', 208: 'group', 209: 'location'}
            arrprocessscope = {201: 'topic', 202: 'movie', 203: 'serie', 204: 'person', 205: 'company', 206: 'network', 209: 'location'}
            strservervariablenametopicid = strservervariableprefix + "topic" + "id"
            strservervariablenamemovieid = strservervariableprefix + "movie" + "id"
            strservervariablenameserieid = strservervariableprefix + "serie" + "id"
            strservervariablenamepersonid = strservervariableprefix + "person" + "id"
            strservervariablenamecompanyid = strservervariableprefix + "company" + "id"
            strservervariablenamenetworkid = strservervariableprefix + "network" + "id"
            strservervariablenamecharacterid = strservervariableprefix + "character" + "id"
            strservervariablenamegroupid = strservervariableprefix + "group" + "id"
            strservervariablenamelocationid = strservervariableprefix + "location" + "id"
            strtopicidold = cp.f_getservervariable(strservervariablenametopicid,0)
            strmovieidold = cp.f_getservervariable(strservervariablenamemovieid,0)
            strserieidold = cp.f_getservervariable(strservervariablenameserieid,0)
            strpersonidold = cp.f_getservervariable(strservervariablenamepersonid,0)
            strcompanyidold = cp.f_getservervariable(strservervariablenamecompanyid,0)
            strnetworkidold = cp.f_getservervariable(strservervariablenamenetworkid,0)
            strcharacteridold = cp.f_getservervariable(strservervariablenamecharacterid,0)
            strgroupidold = cp.f_getservervariable(strservervariablenamegroupid,0)
            strlocationidold = cp.f_getservervariable(strservervariablenamelocationid,0)

            strcurrentcontent = cp.f_getservervariable(strservervariablenamecurrentcontent,0)
            
            if strcurrentcontent == "movie":
                arrprocessscope = {202: 'movie', 203: 'serie', 204: 'person', 205: 'company', 206: 'network', 209: 'location'}
            elif strcurrentcontent == "serie":
                arrprocessscope = {203: 'serie', 204: 'person', 205: 'company', 206: 'network', 209: 'location'}
            elif strcurrentcontent == "person":
                arrprocessscope = {204: 'person', 205: 'company', 206: 'network', 209: 'location'}
            elif strcurrentcontent == "company":
                arrprocessscope = {205: 'company', 206: 'network', 209: 'location'}
            elif strcurrentcontent == "network":
                arrprocessscope = {206: 'network', 209: 'location'}
            elif strcurrentcontent == "location":
                arrprocessscope = {209: 'location'}
            """
            elif strcurrentcontent == "character":
                arrprocessscope = {207: 'character', 208: 'group'}
            elif strcurrentcontent == "group":
                arrprocessscope = {208: 'group'}
            """
            if strprocessstart.startswith('2026-03-03'):
                # Tesing location embeddings update
                arrprocessscope = {209: 'location'}
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
                    print("Create embeddings for the " + strentitycollection)

                    strservervariablenameid = strservervariableprefix + strentityname + "id"
                    strservervariablenamestartdatetime = strservervariableprefix + strentityname + "startdatetime"
                    strservervariablenamedeletereport = strservervariableprefix + strentityname + "deletereport"
                    strservervariablenamenotdeletereport = strservervariableprefix + strentityname + "notdeletereport"

                    strtopicstartdatetimeprevious = cp.f_getservervariable(strservervariablenamestartdatetime,0)
                    strprocessstart = datetime.now(cp.paris_tz).strftime("%Y-%m-%d %H:%M:%S")

                    strsql = ""
                    strsql += "SELECT DISTINCT " + strkeyfieldname + ", ID_RECORD, 'en' AS ENGLISH_LANGUAGE, TOPIC_NAME AS ENGLISH_NAME, 'fr' AS FRENCH_LANGUAGE, TOPIC_NAME_FR AS FRENCH_NAME, OVERVIEW, TOPIC_TYPE, DELETED, MOVIE_COUNT, SERIE_COUNT "
                    strsql += "FROM " + strtablename + " "
                    if strtopicidold != "":
                        strsql += "WHERE " + strkeyfieldname + " >= " + strtopicidold + " "
                    if strtopicstartdatetimeprevious is not None and str(strtopicstartdatetimeprevious).strip() != "":
                        strtopicstartdatetimeprevious = str(strtopicstartdatetimeprevious).strip().replace("'", "''")
                        if strtopicidold != "":
                            strsql += "AND TIM_UPDATED >= '" + strtopicstartdatetimeprevious + "' "
                        else:
                            strsql += "WHERE TIM_UPDATED >= '" + strtopicstartdatetimeprevious + "' "
                    strsql += "ORDER BY " + strkeyfieldname + " ASC "
                    try:
                        cursor.execute(strsql)
                    except Exception:
                        strsql = ""
                        strsql += "SELECT DISTINCT " + strkeyfieldname + ", ID_RECORD, 'en' AS ENGLISH_LANGUAGE, TOPIC_NAME AS ENGLISH_NAME, 'fr' AS FRENCH_LANGUAGE, TOPIC_NAME_FR AS FRENCH_NAME, OVERVIEW, TOPIC_TYPE, DELETED, MOVIE_COUNT, SERIE_COUNT "
                        strsql += "FROM " + strtablename + " "
                        if strtopicidold != "":
                            strsql += "WHERE " + strkeyfieldname + " >= " + strtopicidold + " "
                        strsql += "ORDER BY " + strkeyfieldname + " ASC "
                        cursor.execute(strsql)
                    lngrowcount = cursor.rowcount
                    print(f"{lngrowcount} lines")
                    results = cursor.fetchall()
                    for row in results:
                        lngtopicid = row[strkeyfieldname]
                        cp.f_setservervariable(strservervariablenameid,str(lngtopicid),f"Current {strentityname} ID in the embedding update process",0)
                        arrlanguage = {}
                        arrtitle = {}
                        arrlanguage['en'] = (row.get('ENGLISH_LANGUAGE') or '').strip()
                        arrtitle['en'] = (row.get('ENGLISH_NAME') or '').strip()
                        arrlanguage['fr'] = (row.get('FRENCH_LANGUAGE') or '').strip()
                        arrtitle['fr'] = (row.get('FRENCH_NAME') or '').strip()

                        strtopicoverview = (row.get('OVERVIEW') or '').strip()
                        lngtopictype = row['TOPIC_TYPE']
                        intdeleted = row['DELETED']
                        lngmoviecount = row['MOVIE_COUNT']
                        lngseriecount = row['SERIE_COUNT']
                        lngelementcount = lngmoviecount + lngseriecount
                        strtopicoverview = strtopicoverview.replace("\n", " ")

                        # Process embeddings for each title in each language
                        for lang_code in arrlanguage.keys():
                            if lang_code in arrtitle and arrtitle[lang_code].strip() != "":
                                strtopictitle = arrtitle[lang_code].strip()
                                strtopiclang = arrlanguage[lang_code].strip()
                                strdocid = strentityname + "id_" + str(lngtopicid) + "_" + strtopiclang
                                strtopicfulldesc = strtopictitle
                                if strtopicoverview != "":
                                    strtopicfulldesc += ": " + strtopicoverview
                                if len(strtopicfulldesc) > max_chars:
                                    strtopicfulldesc = strtopicfulldesc[:max_chars] + "..."

                                # Check if the document content already exists in ChromaDB
                                existing_doc = topics.get(ids=[strdocid])

                                if intdeleted == 1 or lngelementcount <= 1:
                                    # This document was deleted in the source database
                                    # Or this topic has no element or a single element
                                    # So we must delete it in ChromaDB
                                    if existing_doc and len(existing_doc['ids']) > 0:
                                        topics.delete(ids=[strdocid])
                                        print(f"{strkeyfieldname}: {lngtopicid}, {strtopicfulldesc} ({strtopiclang}) -> DELETED")
                                    continue

                                if existing_doc and len(existing_doc['ids']) > 0:
                                    strdoctext = existing_doc['documents'][0]
                                    if strdoctext == strtopicfulldesc:
                                        continue

                                # Check if the document exists in ChromaDB
                                if existing_doc and len(existing_doc['ids']) > 0:
                                    topics.update(
                                        ids=[strdocid],
                                        documents=[strtopicfulldesc]  # New updated text
                                    )
                                    print(f"{strkeyfieldname}: {lngtopicid}, {strtopicfulldesc} ({strtopiclang}) -> UPDATED")
                                else:
                                    topics.add(
                                        ids=[strdocid],
                                        documents=[strtopicfulldesc]
                                    )
                                    print(f"{strkeyfieldname}: {lngtopicid}, {strtopicfulldesc} ({strtopiclang}) -> ADDED")
                    # Now delete all topic embeddings that do not exist anymore in the T2S_TOPIC table
                    print(f"Delete all {strentityname} embeddings that do not exist anymore in the {strtablename} table")
                    batch_size = 1000
                    offset = 0
                    lngdeletedcount = 0
                    lngnondeletedcount = 0
                    while True:
                        # Step 1: get all ids from topics
                        results = topics.get(include=[], limit=batch_size, offset=offset)
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
                            strsql = "SELECT " + strkeyfieldname + " FROM " + strtablename + " WHERE " + strkeyfieldname + " = " + docid
                            #print(strsql)
                            cursor.execute(strsql)
                            lngrowcount = cursor.rowcount
                            if lngrowcount == 0:
                                topics.delete(ids=[id])
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
                elif intindex == 202:
                    # Create embeddings for the movies
                    strentityname = "movie"
                    strentitycollection = "movies"
                    strtablename = "T_WC_T2S_MOVIE"
                    strtablelang = "T_WC_TMDB_MOVIE_LANG"
                    strkeyfieldname = "ID_MOVIE"
                    print("Create embeddings for the " + strentitycollection)

                    strservervariablenameid = strservervariableprefix + strentityname + "id"
                    strservervariablenamestartdatetime = strservervariableprefix + strentityname + "startdatetime"
                    strservervariablenamedeletereport = strservervariableprefix + strentityname + "deletereport"
                    strservervariablenamenotdeletereport = strservervariableprefix + strentityname + "notdeletereport"

                    strmoviestartdatetimeprevious = cp.f_getservervariable(strservervariablenamestartdatetime,0)
                    strprocessstart = datetime.now(cp.paris_tz).strftime("%Y-%m-%d %H:%M:%S")

                    strsql = "SELECT DISTINCT " + strtablename + "." + strkeyfieldname + ", " + strtablename + ".ID_WIKIDATA, 'en' AS ENGLISH_LANGUAGE, " + strtablename + ".MOVIE_TITLE AS ENGLISH_TITLE, " + strtablename + ".ORIGINAL_LANGUAGE, " + strtablename + ".ORIGINAL_TITLE, " + strtablelang + ".LANG AS FRENCH_LANGUAGE, " + strtablelang + ".TITLE AS FRENCH_TITLE, " + strtablename + ".DELETED "
                    strsql += "FROM " + strtablename + " "
                    strsql += "LEFT JOIN " + strtablelang + " ON " + strtablename + "." + strkeyfieldname + " = " + strtablelang + "." + strkeyfieldname + " "
                    strsql += "WHERE " + strtablelang + ".LANG = 'fr' "
                    if strmovieidold != "":
                        strsql += "AND " + strtablename + "." + strkeyfieldname + " >= " + strmovieidold + " "
                    if strmoviestartdatetimeprevious is not None and str(strmoviestartdatetimeprevious).strip() != "":
                        strmoviestartdatetimeprevious = str(strmoviestartdatetimeprevious).strip().replace("'", "''")
                        strsql += "AND " + strtablename + ".TIM_UPDATED >= '" + strmoviestartdatetimeprevious + "' "
                    strsql += "ORDER BY " + strtablename + "." + strkeyfieldname + " ASC "
                    try:
                        cursor.execute(strsql)
                    except Exception:
                        strsql = "SELECT DISTINCT " + strtablename + "." + strkeyfieldname + ", " + strtablename + ".ID_WIKIDATA, 'en' AS ENGLISH_LANGUAGE, " + strtablename + ".MOVIE_TITLE AS ENGLISH_TITLE, " + strtablename + ".ORIGINAL_LANGUAGE, " + strtablename + ".ORIGINAL_TITLE, " + strtablelang + ".LANG AS FRENCH_LANGUAGE, " + strtablelang + ".TITLE AS FRENCH_TITLE, " + strtablename + ".DELETED "
                        strsql += "FROM " + strtablename + " "
                        strsql += "LEFT JOIN " + strtablelang + " ON " + strtablename + "." + strkeyfieldname + " = " + strtablelang + "." + strkeyfieldname + " "
                        strsql += "WHERE " + strtablelang + ".LANG = 'fr' "
                        if strmovieidold != "":
                            strsql += "AND " + strtablename + "." + strkeyfieldname + " >= " + strmovieidold + " "
                        strsql += "ORDER BY " + strtablename + "." + strkeyfieldname + " ASC "
                        cursor.execute(strsql)
                    lngrowcount = cursor.rowcount
                    print(f"{lngrowcount} lines")
                    results = cursor.fetchall()
                    for row in results:
                        lngmovieid = row[strkeyfieldname]
                        cp.f_setservervariable(strservervariablenameid,str(lngmovieid),f"Current {strentityname} ID in the embedding update process",0)
                        strwikidataid = row['ID_WIKIDATA'].strip()
                        arrlanguage = {}
                        arrtitle = {}
                        arrlanguage['en'] = row['ENGLISH_LANGUAGE'].strip()
                        arrtitle['en'] = row['ENGLISH_TITLE'].strip()
                        arrlanguage['fr'] = row['FRENCH_LANGUAGE'].strip()
                        arrtitle['fr'] = row['FRENCH_TITLE'].strip()
                        strlang = row['ORIGINAL_LANGUAGE'].strip()
                        if strlang != "" and strlang not in arrlanguage:
                            arrtitle[strlang] = row['ORIGINAL_TITLE'].strip()
                            arrlanguage[strlang] = strlang
                        intdeleted = row['DELETED']
                        if strwikidataid == "":
                            # No Wikidata id, so we must delete it in ChromaDB
                            intdeleted = 1
                        
                        # Process embeddings for each title in each language
                        for lang_code in arrlanguage.keys():
                            if lang_code in arrtitle and arrtitle[lang_code].strip() != "":
                                strmovietitle = arrtitle[lang_code].strip()
                                strmovielang = arrlanguage[lang_code].strip()
                                strdocid = strentityname + "id_" + str(lngmovieid) + "_" + strmovielang
                                strmoviefulldesc = strmovietitle
                                
                                # Check if the document content already exists in ChromaDB
                                # First check by ID
                                existing_doc = movies.get(ids=[strdocid])
                                
                                if intdeleted == 1:
                                    # This document was deleted in the source database
                                    # So we must delete it in ChromaDB
                                    if existing_doc and len(existing_doc['ids']) > 0:
                                        movies.delete(ids=[strdocid])
                                        print(f"{strkeyfieldname}: {lngmovieid}, {strmoviefulldesc} ({strmovielang}) -> DELETED")
                                    continue
                                
                                if existing_doc and len(existing_doc['ids']) > 0:
                                    strdoctext = existing_doc['documents'][0]
                                    if strdoctext == strmoviefulldesc:
                                        # This document was already processed to an embedding
                                        # Nothing to do 
                                        #print(f"{strkeyfieldname}: {lngmovieid}, {strmoviefulldesc} ({strmovielang}) -> ALREADY PROCESSED")
                                        continue
                                
                                # Check if the content already exists anywhere in the collection (case-insensitive)
                                try:
                                    search_results = movies.query(
                                        query_texts=[strmoviefulldesc],
                                        n_results=1
                                    )
                                    if (search_results["documents"] and 
                                        len(search_results["documents"][0]) > 0 and 
                                        search_results["documents"][0][0].lower() == strmoviefulldesc.lower()):
                                        #print(f"{strkeyfieldname}: {lngmovieid}, {strmoviefulldesc} ({strmovielang}) -> CONTENT ALREADY EXISTS")
                                        continue
                                except Exception as e:
                                    # If query fails, continue with normal processing
                                    print(f"Warning: Could not check for existing content: {e}")
                                    pass
                                
                                # Check if the document exists in ChromaDB
                                if existing_doc and len(existing_doc['ids']) > 0:
                                    # If the document exists, update it
                                    movies.update(
                                        ids=[strdocid],
                                        documents=[strmoviefulldesc]
                                    )
                                    print(f"{strkeyfieldname}: {lngmovieid}, {strmoviefulldesc} ({strmovielang}) -> UPDATED")
                                else:
                                    # If the document does not exist, add it
                                    movies.add(
                                        ids=[strdocid],
                                        documents=[strmoviefulldesc]
                                    )
                                    print(f"{strkeyfieldname}: {lngmovieid}, {strmoviefulldesc} ({strmovielang}) -> ADDED")
                    # Now delete all movie embeddings that do not exist anymore in the T2S_MOVIE table
                    print(f"Delete all {strentityname} embeddings that do not exist anymore in the {strtablename} table")
                    batch_size = 1000
                    offset = 0
                    lngdeletedcount = 0
                    lngnondeletedcount = 0
                    while True:
                        # Step 1: get all ids from movies
                        results = movies.get(include=[], limit=batch_size, offset=offset)
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
                            strsql = "SELECT " + strkeyfieldname + " FROM " + strtablename + " WHERE " + strkeyfieldname + " = " + docid + " "
                            #print(strsql)
                            cursor.execute(strsql)
                            lngrowcount = cursor.rowcount
                            if lngrowcount == 0:
                                movies.delete(ids=[id])
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
                elif intindex == 203:
                    # Create embeddings for the series
                    strentityname = "serie"
                    strentitycollection = "series"
                    strtablename = "T_WC_T2S_SERIE"
                    strtablelang = "T_WC_TMDB_SERIE_LANG"
                    strkeyfieldname = "ID_SERIE"
                    print("Create embeddings for the " + strentitycollection)

                    strservervariablenameid = strservervariableprefix + strentityname + "id"
                    strservervariablenamestartdatetime = strservervariableprefix + strentityname + "startdatetime"
                    strservervariablenamedeletereport = strservervariableprefix + strentityname + "deletereport"
                    strservervariablenamenotdeletereport = strservervariableprefix + strentityname + "notdeletereport"

                    strseriestartdatetimeprevious = cp.f_getservervariable(strservervariablenamestartdatetime,0)
                    strprocessstart = datetime.now(cp.paris_tz).strftime("%Y-%m-%d %H:%M:%S")

                    strsql = "SELECT DISTINCT " + strtablename + "." + strkeyfieldname + ", " + strtablename + ".ID_WIKIDATA, 'en' AS ENGLISH_LANGUAGE, " + strtablename + ".SERIE_TITLE AS ENGLISH_TITLE, " + strtablename + ".ORIGINAL_LANGUAGE, " + strtablename + ".ORIGINAL_TITLE, " + strtablelang + ".LANG AS FRENCH_LANGUAGE, " + strtablelang + ".TITLE AS FRENCH_TITLE, " + strtablename + ".DELETED "
                    strsql += "FROM " + strtablename + " "
                    strsql += "LEFT JOIN " + strtablelang + " ON " + strtablename + "." + strkeyfieldname + " = " + strtablelang + "." + strkeyfieldname + " "
                    strsql += "WHERE " + strtablelang + ".LANG = 'fr' "
                    if strserieidold != "":
                        strsql += "AND " + strtablename + "." + strkeyfieldname + " >= " + strserieidold + " "
                    if strseriestartdatetimeprevious is not None and str(strseriestartdatetimeprevious).strip() != "":
                        strseriestartdatetimeprevious = str(strseriestartdatetimeprevious).strip().replace("'", "''")
                        strsql += "AND " + strtablename + ".TIM_UPDATED >= '" + strseriestartdatetimeprevious + "' "
                    strsql += "ORDER BY " + strtablename + "." + strkeyfieldname + " ASC "
                    try:
                        cursor.execute(strsql)
                    except Exception:
                        strsql = "SELECT DISTINCT " + strtablename + "." + strkeyfieldname + ", " + strtablename + ".ID_WIKIDATA, 'en' AS ENGLISH_LANGUAGE, " + strtablename + ".SERIE_TITLE AS ENGLISH_TITLE, " + strtablename + ".ORIGINAL_LANGUAGE, " + strtablename + ".ORIGINAL_TITLE, " + strtablelang + ".LANG AS FRENCH_LANGUAGE, " + strtablelang + ".TITLE AS FRENCH_TITLE, " + strtablename + ".DELETED "
                        strsql += "FROM " + strtablename + " "
                        strsql += "LEFT JOIN " + strtablelang + " ON " + strtablename + "." + strkeyfieldname + " = " + strtablelang + "." + strkeyfieldname + " "
                        strsql += "WHERE " + strtablelang + ".LANG = 'fr' "
                        if strserieidold != "":
                            strsql += "AND " + strtablename + "." + strkeyfieldname + " >= " + strserieidold + " "
                        strsql += "ORDER BY " + strtablename + "." + strkeyfieldname + " ASC "
                        cursor.execute(strsql)
                    lngrowcount = cursor.rowcount
                    print(f"{lngrowcount} lines")
                    results = cursor.fetchall()
                    for row in results:
                        lngserieid = row[strkeyfieldname]
                        cp.f_setservervariable(strservervariablenameid,str(lngserieid),f"Current {strentityname} ID in the embedding update process",0)
                        strwikidataid = row['ID_WIKIDATA'].strip()
                        arrlanguage = {}
                        arrtitle = {}
                        arrlanguage['en'] = row['ENGLISH_LANGUAGE'].strip()
                        arrtitle['en'] = row['ENGLISH_TITLE'].strip()
                        arrlanguage['fr'] = row['FRENCH_LANGUAGE'].strip()
                        arrtitle['fr'] = row['FRENCH_TITLE'].strip()
                        strlang = row['ORIGINAL_LANGUAGE'].strip()
                        if strlang != "" and strlang not in arrlanguage:
                            arrtitle[strlang] = row['ORIGINAL_TITLE'].strip()
                            arrlanguage[strlang] = strlang
                        intdeleted = row['DELETED']
                        if strwikidataid == "":
                            # No Wikidata id, so we must delete it in ChromaDB
                            intdeleted = 1
                        
                        # Process embeddings for each title in each language
                        for lang_code in arrlanguage.keys():
                            if lang_code in arrtitle and arrtitle[lang_code].strip() != "":
                                strserietitle = arrtitle[lang_code].strip()
                                strserielang = arrlanguage[lang_code].strip()
                                strdocid = strentityname + "id_" + str(lngserieid) + "_" + strserielang
                                strseriefulldesc = strserietitle
                                
                                # Check if the document content already exists in ChromaDB
                                # First check by ID
                                existing_doc = series.get(ids=[strdocid])
                                
                                if intdeleted == 1:
                                    # This document was deleted in the source database
                                    # So we must delete it in ChromaDB
                                    if existing_doc and len(existing_doc['ids']) > 0:
                                        series.delete(ids=[strdocid])
                                        print(f"{strkeyfieldname}: {lngserieid}, {strseriefulldesc} ({strserielang}) -> DELETED")
                                    continue
                                
                                if existing_doc and len(existing_doc['ids']) > 0:
                                    strdoctext = existing_doc['documents'][0]
                                    if strdoctext == strseriefulldesc:
                                        # This document was already processed to an embedding
                                        # Nothing to do 
                                        #print(f"{strkeyfieldname}: {lngmovieid}, {strmoviefulldesc} ({strmovielang}) -> ALREADY PROCESSED")
                                        continue
                                
                                # Check if the content already exists anywhere in the collection (case-insensitive)
                                try:
                                    search_results = series.query(
                                        query_texts=[strseriefulldesc],
                                        n_results=1
                                    )
                                    if (search_results["documents"] and 
                                        len(search_results["documents"][0]) > 0 and 
                                        search_results["documents"][0][0].lower() == strseriefulldesc.lower()):
                                        #print(f"{strkeyfieldname}: {lngserieid}, {strseriefulldesc} ({strserielang}) -> CONTENT ALREADY EXISTS")
                                        continue
                                except Exception as e:
                                    # If query fails, continue with normal processing
                                    print(f"Warning: Could not check for existing content: {e}")
                                    pass
                                
                                # Check if the document exists in ChromaDB
                                if existing_doc and len(existing_doc['ids']) > 0:
                                    # If the document exists, update it
                                    series.update(
                                        ids=[strdocid],
                                        documents=[strseriefulldesc]
                                    )
                                    print(f"{strkeyfieldname}: {lngserieid}, {strseriefulldesc} ({strserielang}) -> UPDATED")
                                else:
                                    # If the document does not exist, add it
                                    series.add(
                                        ids=[strdocid],
                                        documents=[strseriefulldesc]
                                    )
                                    print(f"{strkeyfieldname}: {lngserieid}, {strseriefulldesc} ({strserielang}) -> ADDED")
                    # Now delete all serie embeddings that do not exist anymore in the T2S_SERIE table
                    print(f"Delete all {strentityname} embeddings that do not exist anymore in the {strtablename} table")
                    batch_size = 1000
                    offset = 0
                    lngdeletedcount = 0
                    lngnondeletedcount = 0
                    while True:
                        # Step 1: get all ids from series
                        results = series.get(include=[], limit=batch_size, offset=offset)
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
                            strsql = "SELECT " + strkeyfieldname + " FROM " + strtablename + " WHERE " + strkeyfieldname + " = " + docid + " "
                            #print(strsql)
                            cursor.execute(strsql)
                            lngrowcount = cursor.rowcount
                            if lngrowcount == 0:
                                series.delete(ids=[id])
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
                elif intindex == 204:
                    # Create embeddings for the persons
                    strentityname = "person"
                    strentitycollection = "persons"
                    strtablename = "T_WC_T2S_PERSON"
                    strkeyfieldname = "ID_PERSON"
                    print("Create embeddings for the " + strentitycollection)

                    strservervariablenameid = strservervariableprefix + strentityname + "id"
                    strservervariablenamestartdatetime = strservervariableprefix + strentityname + "startdatetime"
                    strservervariablenamedeletereport = strservervariableprefix + strentityname + "deletereport"
                    strservervariablenamenotdeletereport = strservervariableprefix + strentityname + "notdeletereport"

                    strpersonstartdatetimeprevious = cp.f_getservervariable(strservervariablenamestartdatetime,0)
                    strprocessstart = datetime.now(cp.paris_tz).strftime("%Y-%m-%d %H:%M:%S")

                    strsql = ""
                    strsql += "SELECT " + strkeyfieldname + ", PERSON_NAME, DELETED "
                    strsql += "FROM " + strtablename + " "
                    if strpersonidold != "":
                        strsql += "WHERE " + strkeyfieldname + " >= " + strpersonidold + " "
                    if strpersonstartdatetimeprevious is not None and str(strpersonstartdatetimeprevious).strip() != "":
                        strpersonstartdatetimeprevious = str(strpersonstartdatetimeprevious).strip().replace("'", "''")
                        if strpersonidold != "":
                            strsql += "AND TIM_UPDATED >= '" + strpersonstartdatetimeprevious + "' "
                        else:
                            strsql += "WHERE TIM_UPDATED >= '" + strpersonstartdatetimeprevious + "' "
                    strsql += "ORDER BY " + strkeyfieldname + " ASC "
                    try:
                        cursor.execute(strsql)
                    except Exception:
                        strsql = ""
                        strsql += "SELECT " + strkeyfieldname + ", PERSON_NAME, DELETED "
                        strsql += "FROM " + strtablename + " "
                        if strpersonidold != "":
                            strsql += "WHERE " + strkeyfieldname + " >= " + strpersonidold + " "
                        strsql += "ORDER BY " + strkeyfieldname + " ASC "
                        cursor.execute(strsql)
                    lngrowcount = cursor.rowcount
                    print(f"{lngrowcount} lines")
                    results = cursor.fetchall()
                    for row in results:
                        lngpersonid = row[strkeyfieldname]
                        cp.f_setservervariable(strservervariablenameid,str(lngpersonid),f"Current {strentityname} ID in the embedding update process",0)
                        strpersonname = row['PERSON_NAME'].strip()
                        intdeleted = row['DELETED']
                        strdocid = strentityname + "id_" + str(lngpersonid) + "_en"
                        strpersonfulldesc = strpersonname
                        if len(strpersonfulldesc) > max_chars:
                            strpersonfulldesc = strpersonfulldesc[:max_chars] + "..."
                        existing_doc = persons.get(ids=[strdocid])
                        if existing_doc and len(existing_doc['ids']) > 0:
                            strdoctext = existing_doc['documents'][0]
                            if strdoctext == strpersonfulldesc:
                                # This document was already processed to an embedding
                                # Nothing to do 
                                #print(f"{strkeyfieldname}: {lngpersonid}, {strpersonfulldesc} -> ALREADY PROCESSED")
                                continue
                        if intdeleted == 1:
                            # This document was deleted in the source database
                            # So we must delete it in ChromaDB
                            if existing_doc and len(existing_doc['ids']) > 0:
                                persons.delete(ids=[strdocid])
                                print(f"{strkeyfieldname}: {lngpersonid}, {strpersonfulldesc} -> DELETED")
                                continue
                        # Check if the document exists in ChromaDB
                        if existing_doc and len(existing_doc['ids']) > 0:
                            # If the document exists, update it
                            persons.update(
                                ids=[strdocid],
                                documents=[strpersonfulldesc]  # New updated text
                            )
                            print(f"{strkeyfieldname}: {lngpersonid}, {strpersonfulldesc} -> UPDATED")
                        else:
                            # If the document does not exist, add it
                            persons.add(
                                ids=[strdocid],
                                documents=[strpersonfulldesc]
                            )
                            print(f"{strkeyfieldname}: {lngpersonid}, {strpersonfulldesc} -> ADDED")
                    # Now delete all person embeddings that do not exist anymore in the T2S_PERSON table
                    print(f"Delete all {strentityname} embeddings that do not exist anymore in the {strtablename} table")
                    batch_size = 1000
                    offset = 0
                    lngdeletedcount = 0
                    lngnondeletedcount = 0
                    while True:
                        # Step 1: get all ids from persons
                        results = persons.get(include=[], limit=batch_size, offset=offset)
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
                            strsql = "SELECT " + strkeyfieldname + " FROM " + strtablename + " WHERE " + strkeyfieldname + " = " + docid + " "
                            #print(strsql)
                            cursor.execute(strsql)
                            lngrowcount = cursor.rowcount
                            if lngrowcount == 0:
                                persons.delete(ids=[id])
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
                elif intindex == 205:
                    # Create embeddings for the companies
                    strentityname = "company"
                    strentitycollection = "companies"
                    strtablename = "T_WC_T2S_COMPANY"
                    strkeyfieldname = "ID_COMPANY"
                    print("Create embeddings for the " + strentitycollection)

                    strservervariablenameid = strservervariableprefix + strentityname + "id"
                    strservervariablenamestartdatetime = strservervariableprefix + strentityname + "startdatetime"
                    strservervariablenamedeletereport = strservervariableprefix + strentityname + "deletereport"
                    strservervariablenamenotdeletereport = strservervariableprefix + strentityname + "notdeletereport"

                    strcompanystartdatetimeprevious = cp.f_getservervariable(strservervariablenamestartdatetime,0)
                    strprocessstart = datetime.now(cp.paris_tz).strftime("%Y-%m-%d %H:%M:%S")

                    strsql = ""
                    strsql += "SELECT " + strkeyfieldname + ", COMPANY_NAME, DELETED "
                    strsql += "FROM " + strtablename + " "
                    if strcompanyidold != "":
                        strsql += "WHERE " + strkeyfieldname + " >= " + strcompanyidold + " "
                    if strcompanystartdatetimeprevious is not None and str(strcompanystartdatetimeprevious).strip() != "":
                        strcompanystartdatetimeprevious = str(strcompanystartdatetimeprevious).strip().replace("'", "''")
                        if strcompanyidold != "":
                            strsql += "AND TIM_UPDATED >= '" + strcompanystartdatetimeprevious + "' "
                        else:
                            strsql += "WHERE TIM_UPDATED >= '" + strcompanystartdatetimeprevious + "' "
                    strsql += "ORDER BY " + strkeyfieldname + " ASC "
                    print(strsql)
                    try:
                        cursor.execute(strsql)
                    except Exception:
                        strsql = ""
                        strsql += "SELECT " + strkeyfieldname + ", COMPANY_NAME, DELETED "
                        strsql += "FROM " + strtablename + " "
                        if strcompanyidold != "":
                            strsql += "WHERE " + strkeyfieldname + " >= " + strcompanyidold + " "
                        strsql += "ORDER BY " + strkeyfieldname + " ASC "
                        print(strsql)
                        cursor.execute(strsql)
                    lngrowcount = cursor.rowcount
                    print(f"{lngrowcount} lines")
                    results = cursor.fetchall()
                    for row in results:
                        lngcompanyid = row[strkeyfieldname]
                        cp.f_setservervariable(strservervariablenameid,str(lngcompanyid),f"Current {strentityname} ID in the embedding update process",0)
                        strcompanyname = row['COMPANY_NAME'].strip()
                        intdeleted = row['DELETED']
                        strdocid = strentityname + "id_" + str(lngcompanyid) + "_en"
                        strcompanyfulldesc = strcompanyname
                        if len(strcompanyfulldesc) > max_chars:
                            strcompanyfulldesc = strcompanyfulldesc[:max_chars] + "..."
                        """
                        if lngcompanyid <= 60:
                            companies.add(
                                ids=[strdocid],
                                documents=[strcompanyfulldesc]
                            )
                            print(f"{strkeyfieldname}: {lngcompanyid}, {strcompanyfulldesc} -> ADDED FORCED")
                        """
                        existing_doc = companies.get(ids=[strdocid])
                        if existing_doc and len(existing_doc['ids']) > 0:
                            strdoctext = existing_doc['documents'][0]


                            """ Forcing update if the company ID is less than 60 """
                            if lngcompanyid <= 60:
                                strdoctext = "" 
                            """ Forcing update if the company ID is less than 60 """

                            
                            if strdoctext == strcompanyfulldesc:
                                # This document was already processed to an embedding
                                # Nothing to do 
                                #print(f"{strkeyfieldname}: {lngcompanyid}, {strcompanyfulldesc} -> ALREADY PROCESSED")
                                continue
                        if intdeleted == 1:
                            # This document was deleted in the source database
                            # So we must delete it in ChromaDB
                            if existing_doc and len(existing_doc['ids']) > 0:
                                companies.delete(ids=[strdocid])
                                print(f"{strkeyfieldname}: {lngcompanyid}, {strcompanyfulldesc} -> DELETED")
                                continue
                        # Check if the document exists in ChromaDB
                        if existing_doc and len(existing_doc['ids']) > 0:
                            # If the document exists, update it
                            companies.update(
                                ids=[strdocid],
                                documents=[strcompanyfulldesc]  # New updated text
                            )
                            print(f"{strkeyfieldname}: {lngcompanyid}, {strcompanyfulldesc} -> UPDATED")
                        else:
                            # If the document does not exist, add it
                            companies.add(
                                ids=[strdocid],
                                documents=[strcompanyfulldesc]
                            )
                            print(f"{strkeyfieldname}: {lngcompanyid}, {strcompanyfulldesc} -> ADDED")
                    # Now delete all company embeddings that do not exist anymore in the T2S_COMPANY table
                    print(f"Delete all {strentityname} embeddings that do not exist anymore in the {strtablename} table")
                    batch_size = 1000
                    offset = 0
                    lngdeletedcount = 0
                    lngnondeletedcount = 0
                    while True:
                        # Step 1: get all ids from companies
                        results = companies.get(include=[], limit=batch_size, offset=offset)
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
                            strsql = "SELECT " + strkeyfieldname + " FROM " + strtablename + " WHERE " + strkeyfieldname + " = " + docid + " "
                            #print(strsql)
                            cursor.execute(strsql)
                            lngrowcount = cursor.rowcount
                            if lngrowcount == 0:
                                companies.delete(ids=[id])
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
                elif intindex == 206:
                    # Create embeddings for the networks
                    # But define some stuff first:
                    # Populate the T2S_NETWORK table
                    strentityname = "network"
                    strentitycollection = "networks"
                    strtablename = "T_WC_T2S_NETWORK"
                    strkeyfieldname = "ID_NETWORK"
                    print("Create embeddings for the " + strentitycollection)

                    strservervariablenameid = strservervariableprefix + strentityname + "id"
                    strservervariablenamestartdatetime = strservervariableprefix + strentityname + "startdatetime"
                    strservervariablenamedeletereport = strservervariableprefix + strentityname + "deletereport"
                    strservervariablenamenotdeletereport = strservervariableprefix + strentityname + "notdeletereport"

                    strnetworkstartdatetimeprevious = cp.f_getservervariable(strservervariablenamestartdatetime,0)
                    strprocessstart = datetime.now(cp.paris_tz).strftime("%Y-%m-%d %H:%M:%S")

                    strsql = ""
                    strsql += "SELECT " + strkeyfieldname + ", NETWORK_NAME, DELETED "
                    strsql += "FROM " + strtablename + " "
                    if strnetworkidold != "":
                        strsql += "WHERE " + strkeyfieldname + " >= " + strnetworkidold + " "
                    if strnetworkstartdatetimeprevious is not None and str(strnetworkstartdatetimeprevious).strip() != "":
                        strnetworkstartdatetimeprevious = str(strnetworkstartdatetimeprevious).strip().replace("'", "''")
                        if strnetworkidold != "":
                            strsql += "AND TIM_UPDATED >= '" + strnetworkstartdatetimeprevious + "' "
                        else:
                            strsql += "WHERE TIM_UPDATED >= '" + strnetworkstartdatetimeprevious + "' "
                    strsql += "ORDER BY " + strkeyfieldname + " ASC "
                    try:
                        cursor.execute(strsql)
                    except Exception:
                        strsql = ""
                        strsql += "SELECT " + strkeyfieldname + ", NETWORK_NAME, DELETED "
                        strsql += "FROM " + strtablename + " "
                        if strnetworkidold != "":
                            strsql += "WHERE " + strkeyfieldname + " >= " + strnetworkidold + " "
                        strsql += "ORDER BY " + strkeyfieldname + " ASC "
                        cursor.execute(strsql)
                    lngrowcount = cursor.rowcount
                    print(f"{lngrowcount} lines")
                    results = cursor.fetchall()
                    for row in results:
                        lngnetworkid = row[strkeyfieldname]
                        cp.f_setservervariable(strservervariablenameid,str(lngnetworkid),f"Current {strentityname} ID in the embedding update process",0)
                        strnetworkname = row['NETWORK_NAME'].strip()
                        intdeleted = row['DELETED']
                        strdocid = strentityname + "id_" + str(lngnetworkid) + "_en"
                        strnetworkfulldesc = strnetworkname
                        if len(strnetworkfulldesc) > max_chars:
                            strnetworkfulldesc = strnetworkfulldesc[:max_chars] + "..."
                        existing_doc = networks.get(ids=[strdocid])
                        if existing_doc and len(existing_doc['ids']) > 0:
                            strdoctext = existing_doc['documents'][0]
                            if strdoctext == strnetworkfulldesc:
                                # This document was already processed to an embedding
                                # Nothing to do 
                                #print(f"{strkeyfieldname}: {lngnetworkid}, {strnetworkfulldesc} -> ALREADY PROCESSED")
                                continue
                        if intdeleted == 1:
                            # This document was deleted in the source database
                            # So we must delete it in ChromaDB
                            if existing_doc and len(existing_doc['ids']) > 0:
                                networks.delete(ids=[strdocid])
                                print(f"{strkeyfieldname}: {lngnetworkid}, {strnetworkfulldesc} -> DELETED")
                                continue
                        # Check if the document exists in ChromaDB
                        if existing_doc and len(existing_doc['ids']) > 0:
                            # If the document exists, update it
                            networks.update(
                                ids=[strdocid],
                                documents=[strnetworkfulldesc]  # New updated text
                            )
                            print(f"{strkeyfieldname}: {lngnetworkid}, {strnetworkfulldesc} -> UPDATED")
                        else:
                            # If the document does not exist, add it
                            networks.add(
                                ids=[strdocid],
                                documents=[strnetworkfulldesc]
                            )
                            print(f"{strkeyfieldname}: {lngnetworkid}, {strnetworkfulldesc} -> ADDED")
                    # Now delete all network embeddings that do not exist anymore in the T2S_NETWORK table
                    print(f"Delete all {strentityname} embeddings that do not exist anymore in the {strtablename} table")
                    batch_size = 1000
                    offset = 0
                    lngdeletedcount = 0
                    lngnondeletedcount = 0
                    while True:
                        # Step 1: get all ids from networks
                        results = networks.get(include=[], limit=batch_size, offset=offset)
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
                            strsql = "SELECT " + strkeyfieldname + " FROM " + strtablename + " WHERE " + strkeyfieldname + " = " + docid + " "
                            #print(strsql)
                            cursor.execute(strsql)
                            lngrowcount = cursor.rowcount
                            if lngrowcount == 0:
                                networks.delete(ids=[id])
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
                elif intindex == 1207:
                    # Create embeddings for the characters
                    # But define some stuff first:
                    # What is the ID for a character?
                    # Write the SQL query to get the characters
                    strentityname = "character"
                    strentitycollection = "characters"
                    strtablename = "T_WC_T2S_CHARACTER"
                    strkeyfieldname = "ID_CHARACTER"
                    print("Create embeddings for the " + strentitycollection)

                    strservervariablenameid = strservervariableprefix + strentityname + "id"
                    strservervariablenamestartdatetime = strservervariableprefix + strentityname + "startdatetime"
                    strservervariablenamedeletereport = strservervariableprefix + strentityname + "deletereport"
                    strservervariablenamenotdeletereport = strservervariableprefix + strentityname + "notdeletereport"

                    strcharacterstartdatetimeprevious = cp.f_getservervariable(strservervariablenamestartdatetime,0)
                    strprocessstart = datetime.now(cp.paris_tz).strftime("%Y-%m-%d %H:%M:%S")

                    strsql = ""
                    strsql += "SELECT " + strkeyfieldname + ", CHARACTER_NAME, DELETED "
                    strsql += "FROM " + strtablename + " "
                    if strcharacteridold != "":
                        strsql += "WHERE " + strkeyfieldname + " >= " + strcharacteridold + " "
                    if strcharacterstartdatetimeprevious is not None and str(strcharacterstartdatetimeprevious).strip() != "":
                        strcharacterstartdatetimeprevious = str(strcharacterstartdatetimeprevious).strip().replace("'", "''")
                        if strcharacteridold != "":
                            strsql += "AND TIM_UPDATED >= '" + strcharacterstartdatetimeprevious + "' "
                        else:
                            strsql += "WHERE TIM_UPDATED >= '" + strcharacterstartdatetimeprevious + "' "
                    strsql += "ORDER BY " + strkeyfieldname + " ASC "
                    try:
                        cursor.execute(strsql)
                    except Exception:
                        strsql = ""
                        strsql += "SELECT " + strkeyfieldname + ", CHARACTER_NAME, DELETED "
                        strsql += "FROM " + strtablename + " "
                        if strcharacteridold != "":
                            strsql += "WHERE " + strkeyfieldname + " >= " + strcharacteridold + " "
                        strsql += "ORDER BY " + strkeyfieldname + " ASC "
                        cursor.execute(strsql)
                    lngrowcount = cursor.rowcount
                    print(f"{lngrowcount} lines")
                    results = cursor.fetchall()
                    for row in results:
                        lngcharacterid = row[strkeyfieldname]
                        cp.f_setservervariable(strservervariablenameid,str(lngcharacterid),f"Current {strentityname} ID in the embedding update process",0)
                        strcharactername = row['CHARACTER_NAME'].strip()
                        intdeleted = row['DELETED']
                        strdocid = strentityname + "id_" + str(lngcharacterid) + "_en"
                        strcharacterfulldesc = strcharactername
                        if len(strcharacterfulldesc) > max_chars:
                            strcharacterfulldesc = strcharacterfulldesc[:max_chars] + "..."
                        existing_doc = characters.get(ids=[strdocid])
                        if existing_doc and len(existing_doc['ids']) > 0:
                            strdoctext = existing_doc['documents'][0]
                            if strdoctext == strcharacterfulldesc:
                                # This document was already processed to an embedding
                                # Nothing to do 
                                #print(f"{strkeyfieldname}: {lngcharacterid}, {strcharacterfulldesc} -> ALREADY PROCESSED")
                                continue
                        if intdeleted == 1:
                            # This document was deleted in the source database
                            # So we must delete it in ChromaDB
                            if existing_doc and len(existing_doc['ids']) > 0:
                                characters.delete(ids=[strdocid])
                                print(f"{strkeyfieldname}: {lngcharacterid}, {strcharacterfulldesc} -> DELETED")
                                continue
                        # Check if the document exists in ChromaDB
                        if existing_doc and len(existing_doc['ids']) > 0:
                            # If the document exists, update it
                            characters.update(
                                ids=[strdocid],
                                documents=[strcharacterfulldesc]  # New updated text
                            )
                            print(f"{strkeyfieldname}: {lngcharacterid}, {strcharacterfulldesc} -> UPDATED")
                        else:
                            # If the document does not exist, add it
                            characters.add(
                                ids=[strdocid],
                                documents=[strcharacterfulldesc]
                            )
                            print(f"{strkeyfieldname}: {lngcharacterid}, {strcharacterfulldesc} -> ADDED")
                    # Now delete all character embeddings that do not exist anymore in the T2S_CHARACTER table
                    print(f"Delete all {strentityname} embeddings that do not exist anymore in the {strtablename} table")
                    batch_size = 1000
                    offset = 0
                    lngdeletedcount = 0
                    lngnondeletedcount = 0
                    while True:
                        # Step 1: get all ids from characters
                        results = characters.get(include=[], limit=batch_size, offset=offset)
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
                            strsql = "SELECT " + strkeyfieldname + " FROM " + strtablename + " WHERE " + strkeyfieldname + " = " + docid + " "
                            #print(strsql)
                            cursor.execute(strsql)
                            lngrowcount = cursor.rowcount
                            if lngrowcount == 0:
                                characters.delete(ids=[id])
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
                elif intindex == 1208:
                    # Create embeddings for the groups
                    # But define some stuff first:
                    # Create the T2S_GROUP table
                    # Populate the T2S_GROUP table
                    # Write the SQL query to get the groups
                    strentityname = "group"
                    strentitycollection = "groups"
                    strtablename = "T_WC_T2S_GROUP"
                    strkeyfieldname = "ID_GROUP"
                    print("Create embeddings for the " + strentitycollection)

                    strservervariablenameid = strservervariableprefix + strentityname + "id"
                    strservervariablenamestartdatetime = strservervariableprefix + strentityname + "startdatetime"
                    strservervariablenamedeletereport = strservervariableprefix + strentityname + "deletereport"
                    strservervariablenamenotdeletereport = strservervariableprefix + strentityname + "notdeletereport"

                    strgroupstartdatetimeprevious = cp.f_getservervariable(strservervariablenamestartdatetime,0)
                    strprocessstart = datetime.now(cp.paris_tz).strftime("%Y-%m-%d %H:%M:%S")

                    strsql = ""
                    strsql += "SELECT " + strkeyfieldname + ", GROUP_NAME, DELETED "
                    strsql += "FROM " + strtablename + " "
                    if strgroupidold != "":
                        strsql += "WHERE " + strkeyfieldname + " >= " + strgroupidold + " "
                    if strgroupstartdatetimeprevious is not None and str(strgroupstartdatetimeprevious).strip() != "":
                        strgroupstartdatetimeprevious = str(strgroupstartdatetimeprevious).strip().replace("'", "''")
                        if strgroupidold != "":
                            strsql += "AND TIM_UPDATED >= '" + strgroupstartdatetimeprevious + "' "
                        else:
                            strsql += "WHERE TIM_UPDATED >= '" + strgroupstartdatetimeprevious + "' "
                    strsql += "ORDER BY " + strkeyfieldname + " ASC "
                    try:
                        cursor.execute(strsql)
                    except Exception:
                        strsql = ""
                        strsql += "SELECT " + strkeyfieldname + ", GROUP_NAME, DELETED "
                        strsql += "FROM " + strtablename + " "
                        if strgroupidold != "":
                            strsql += "WHERE " + strkeyfieldname + " >= " + strgroupidold + " "
                        strsql += "ORDER BY " + strkeyfieldname + " ASC "
                        cursor.execute(strsql)
                    lngrowcount = cursor.rowcount
                    print(f"{lngrowcount} lines")
                    results = cursor.fetchall()
                    for row in results:
                        lnggroupid = row[strkeyfieldname]
                        cp.f_setservervariable(strservervariablenameid,str(lnggroupid),f"Current {strentityname} ID in the embedding update process",0)
                        strgroupname = row['GROUP_NAME'].strip()
                        intdeleted = row['DELETED']
                        strdocid = strentityname + "id_" + str(lnggroupid) + "_en"
                        strgroupfulldesc = strgroupname
                        if len(strgroupfulldesc) > max_chars:
                            strgroupfulldesc = strgroupfulldesc[:max_chars] + "..."
                        existing_doc = groups.get(ids=[strdocid])
                        if existing_doc and len(existing_doc['ids']) > 0:
                            strdoctext = existing_doc['documents'][0]
                            if strdoctext == strgroupfulldesc:
                                # This document was already processed to an embedding
                                # Nothing to do 
                                #print(f"{strkeyfieldname}: {lnggroupid}, {strgroupfulldesc} -> ALREADY PROCESSED")
                                continue
                        if intdeleted == 1:
                            # This document was deleted in the source database
                            # So we must delete it in ChromaDB
                            if existing_doc and len(existing_doc['ids']) > 0:
                                groups.delete(ids=[strdocid])
                                print(f"{strkeyfieldname}: {lnggroupid}, {strgroupfulldesc} -> DELETED")
                                continue
                        # Check if the document exists in ChromaDB
                        if existing_doc and len(existing_doc['ids']) > 0:
                            # If the document exists, update it
                            groups.update(
                                ids=[strdocid],
                                documents=[strgroupfulldesc]  # New updated text
                            )
                            print(f"{strkeyfieldname}: {lnggroupid}, {strgroupfulldesc} -> UPDATED")
                        else:
                            # If the document does not exist, add it
                            groups.add(
                                ids=[strdocid],
                                documents=[strgroupfulldesc]
                            )
                            print(f"{strkeyfieldname}: {lnggroupid}, {strgroupfulldesc} -> ADDED")
                    # Now delete all group embeddings that do not exist anymore in the T2S_GROUP table
                    print(f"Delete all {strentityname} embeddings that do not exist anymore in the {strtablename} table")
                    batch_size = 1000
                    offset = 0
                    lngdeletedcount = 0
                    lngnondeletedcount = 0
                    while True:
                        # Step 1: get all ids from groups
                        results = groups.get(include=[], limit=batch_size, offset=offset)
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
                            strsql = "SELECT " + strkeyfieldname + " FROM " + strtablename + " WHERE " + strkeyfieldname + " = " + docid + " "
                            #print(strsql)
                            cursor.execute(strsql)
                            lngrowcount = cursor.rowcount
                            if lngrowcount == 0:
                                groups.delete(ids=[id])
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

                        strlocationname = arrtitle['en']
                        intdeleted = row.get('DELETED', 0)
                        # Process embeddings for each title in each language
                        for lang_code in arrlanguage.keys():
                            if lang_code in arrtitle and arrtitle[lang_code].strip() != "":
                                strdocid = strentityname + "id_" + strlocationid + "_" + lang_code
                                strlocationfulldesc = arrtitle[lang_code]
                                if len(strlocationfulldesc) > max_chars:
                                    strlocationfulldesc = strlocationfulldesc[:max_chars] + "..."
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

                if intindex == 209:
                    # Last process is finished
                    cp.f_setservervariable(strservervariablenamecurrentcontent,"","Current content processed in the embedding update process",0)
            # Calculate total runtime and convert to readable format
            end_time = time.time()
            strtotalruntime = int(end_time - start_time)  # Total runtime in seconds
            readable_duration = cp.convert_seconds_to_duration(strtotalruntime)
            cp.f_setservervariable(strservervariablenametotalruntime,readable_duration,strtotalruntimedesc,0)
            print(f"Total runtime: {strtotalruntime} seconds ({readable_duration})")
except pymysql.MySQLError as e:
    print(f"? MySQL Error: {e}")
    cp.connectioncp.rollback()
