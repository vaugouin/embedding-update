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

strprocessesexecutedprevious = cp.f_getservervariable("strembeddingupdateprocessesexecuted",0)
strprocessesexecuteddesc = "List of processes executed in the embedding update process"
cp.f_setservervariable("strembeddingupdateprocessesexecutedprevious",strprocessesexecutedprevious,strprocessesexecuteddesc + " (previous execution)",0)
strprocessesexecuted = ""
cp.f_setservervariable("strembeddingupdateprocessesexecuted",strprocessesexecuted,strprocessesexecuteddesc,0)

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
            strnow = datetime.now(cp.paris_tz).strftime("%Y-%m-%d %H:%M:%S")
            cp.f_setservervariable("strembeddingupdatestartdatetime",strnow,"Date and time of the last start of the embedding update process",0)
            strtotalruntimedesc = "Total runtime of the embedding update process"
            strtotalruntimeprevious = cp.f_getservervariable("strembeddingupdatetotalruntime",0)
            cp.f_setservervariable("strembeddingupdatetotalruntimeprevious",strtotalruntimeprevious,strtotalruntimedesc + " (previous execution)",0)
            strtotalruntime = ""
            cp.f_setservervariable("strembeddingupdatetotalruntime",strtotalruntime,strtotalruntimedesc,0)
            
            # Ensure text length is within text-embedding-3-large model limits (8191 tokens)
            # Approximate 4 characters per token, so limit to ~32,000 characters to be safe
            max_chars = 30000

            #arrprocessscope = {201: 'topic', 202: 'movie', 203: 'serie', 204: 'person', 205: 'company', 206: 'network', 207: 'character', 208: 'group', 209: 'location'}
            arrprocessscope = {201: 'topic', 202: 'movie', 203: 'serie', 204: 'person', 205: 'company', 206: 'network', 209: 'location'}
            strtopicidold = cp.f_getservervariable("strembeddingupdatetopicid",0)
            strmovieidold = cp.f_getservervariable("strembeddingupdatemovieid",0)
            strserieidold = cp.f_getservervariable("strembeddingupdateserieid",0)
            strpersonidold = cp.f_getservervariable("strembeddingupdatepersonid",0)
            strcompanyidold = cp.f_getservervariable("strembeddingupdatecompanyid",0)
            strnetworkidold = cp.f_getservervariable("strembeddingupdatenetworkid",0)
            strcharacteridold = cp.f_getservervariable("strembeddingupdatecharacterid",0)
            strgroupidold = cp.f_getservervariable("strembeddingupdategroupid",0)
            strlocationidold = cp.f_getservervariable("strembeddingupdatelocationid",0)

            strcurrentcontent = cp.f_getservervariable("strembeddingupdatecurrentcontent",0)
            
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
            if strnow.startswith('2026-03-03'):
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
                cp.f_setservervariable("strembeddingupdateprocessesexecuted",strprocessesexecuted,strprocessesexecuteddesc,0)
                cp.f_setservervariable("strembeddingupdatecurrentcontent",strcontent,"Current content processed in the embedding update process",0)
                if intindex == 201:
                    # Create embeddings for the topics
                    strentityname = "topic"
                    strentitycollection = "topics"
                    print("Create embeddings for the " + strentitycollection)
                    strsql = ""
                    strsql += "SELECT DISTINCT ID_TOPIC, ID_RECORD, 'en' AS ENGLISH_LANGUAGE, TOPIC_NAME AS ENGLISH_NAME, 'fr' AS FRENCH_LANGUAGE, TOPIC_NAME_FR AS FRENCH_NAME, OVERVIEW, TOPIC_TYPE, DELETED, MOVIE_COUNT, SERIE_COUNT "
                    strsql += "FROM T_WC_T2S_TOPIC "
                    if strtopicidold != "":
                        strsql += "WHERE ID_TOPIC >= " + strtopicidold + " "
                    strsql += "ORDER BY ID_TOPIC ASC "
                    cursor.execute(strsql)
                    lngrowcount = cursor.rowcount
                    print(f"{lngrowcount} lines")
                    results = cursor.fetchall()
                    for row in results:
                        lngtopicid = row['ID_TOPIC']
                        cp.f_setservervariable("strembeddingupdatetopicid",str(lngtopicid),"Current topic ID in the embedding update process",0)
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
                                        print(f"ID_TOPIC: {lngtopicid}, {strtopicfulldesc} ({strtopiclang}) -> DELETED")
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
                                    print(f"ID_TOPIC: {lngtopicid}, {strtopicfulldesc} ({strtopiclang}) -> UPDATED")
                                else:
                                    topics.add(
                                        ids=[strdocid],
                                        documents=[strtopicfulldesc]
                                    )
                                    print(f"ID_TOPIC: {lngtopicid}, {strtopicfulldesc} ({strtopiclang}) -> ADDED")
                    # Now delete all topic embeddings that do not exist anymore in the T2S_TOPIC table
                    print("Delete all topic embeddings that do not exist anymore in the T2S_TOPIC table")
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
                            strsql = "SELECT ID_TOPIC FROM T_WC_T2S_TOPIC WHERE ID_TOPIC = " + docid
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
                    print(f"Deleted {lngdeletedcount} topic docs")
                    print(f"Not deleted {lngnondeletedcount} topic docs")
                    cp.f_setservervariable("strembeddingupdatetopicdeletereport",f"Deleted {lngdeletedcount} topic docs (enabled)","",0)
                    cp.f_setservervariable("strembeddingupdatetopicnotdeletereport",f"Not deleted {lngnondeletedcount} topic docs","",0)
                    cp.f_setservervariable("strembeddingupdatetopicid","","Current topic ID in the embedding update process",0)
                elif intindex == 202:
                    # Create embeddings for the movies
                    strentityname = "movie"
                    strentitycollection = "movies"
                    print("Create embeddings for the " + strentitycollection)
                    strsql = "SELECT DISTINCT T_WC_T2S_MOVIE.ID_MOVIE, T_WC_T2S_MOVIE.ID_WIKIDATA, 'en' AS ENGLISH_LANGUAGE, T_WC_T2S_MOVIE.MOVIE_TITLE AS ENGLISH_TITLE, T_WC_T2S_MOVIE.ORIGINAL_LANGUAGE, T_WC_T2S_MOVIE.ORIGINAL_TITLE, T_WC_TMDB_MOVIE_LANG.LANG AS FRENCH_LANGUAGE, T_WC_TMDB_MOVIE_LANG.TITLE AS FRENCH_TITLE, T_WC_T2S_MOVIE.DELETED "
                    strsql += "FROM T_WC_T2S_MOVIE "
                    strsql += "LEFT JOIN T_WC_TMDB_MOVIE_LANG ON T_WC_T2S_MOVIE.ID_MOVIE = T_WC_TMDB_MOVIE_LANG.ID_MOVIE "
                    strsql += "WHERE T_WC_TMDB_MOVIE_LANG.LANG = 'fr' "
                    if strmovieidold != "":
                        strsql += "AND T_WC_T2S_MOVIE.ID_MOVIE >= " + strmovieidold + " "
                    strsql += "ORDER BY T_WC_T2S_MOVIE.ID_MOVIE ASC "
                    cursor.execute(strsql)
                    lngrowcount = cursor.rowcount
                    print(f"{lngrowcount} lines")
                    results = cursor.fetchall()
                    for row in results:
                        lngmovieid = row['ID_MOVIE']
                        cp.f_setservervariable("strembeddingupdatemovieid",str(lngmovieid),"Current movie ID in the embedding update process",0)
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
                                        print(f"ID_MOVIE: {lngmovieid}, {strmoviefulldesc} ({strmovielang}) -> DELETED")
                                    continue
                                
                                if existing_doc and len(existing_doc['ids']) > 0:
                                    strdoctext = existing_doc['documents'][0]
                                    if strdoctext == strmoviefulldesc:
                                        # This document was already processed to an embedding
                                        # Nothing to do 
                                        #print(f"ID_MOVIE: {lngmovieid}, {strmoviefulldesc} ({strmovielang}) -> ALREADY PROCESSED")
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
                                        #print(f"ID_MOVIE: {lngmovieid}, {strmoviefulldesc} ({strmovielang}) -> CONTENT ALREADY EXISTS")
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
                                    print(f"ID_MOVIE: {lngmovieid}, {strmoviefulldesc} ({strmovielang}) -> UPDATED")
                                else:
                                    # If the document does not exist, add it
                                    movies.add(
                                        ids=[strdocid],
                                        documents=[strmoviefulldesc]
                                    )
                                    print(f"ID_MOVIE: {lngmovieid}, {strmoviefulldesc} ({strmovielang}) -> ADDED")
                    # Now delete all movie embeddings that do not exist anymore in the T2S_MOVIE table
                    print("Delete all movie embeddings that do not exist anymore in the T2S_MOVIE table")
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
                            strsql = "SELECT ID_MOVIE FROM T_WC_T2S_MOVIE WHERE ID_MOVIE = " + docid + " "
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
                    print(f"Deleted {lngdeletedcount} movie docs")
                    print(f"Not deleted {lngnondeletedcount} movie docs")
                    cp.f_setservervariable("strembeddingupdatemoviedeletereport",f"Deleted {lngdeletedcount} movie docs (enabled)","",0)
                    cp.f_setservervariable("strembeddingupdatemovienotdeletereport",f"Not deleted {lngnondeletedcount} movie docs","",0)
                    cp.f_setservervariable("strembeddingupdatemovieid","","Current movie ID in the embedding update process",0)
                elif intindex == 203:
                    # Create embeddings for the series
                    strentityname = "serie"
                    strentitycollection = "series"
                    print("Create embeddings for the " + strentitycollection)
                    strsql = "SELECT DISTINCT T_WC_T2S_SERIE.ID_SERIE, T_WC_T2S_SERIE.ID_WIKIDATA, 'en' AS ENGLISH_LANGUAGE, T_WC_T2S_SERIE.SERIE_TITLE AS ENGLISH_TITLE, T_WC_T2S_SERIE.ORIGINAL_LANGUAGE, T_WC_T2S_SERIE.ORIGINAL_TITLE, T_WC_TMDB_SERIE_LANG.LANG AS FRENCH_LANGUAGE, T_WC_TMDB_SERIE_LANG.TITLE AS FRENCH_TITLE, T_WC_T2S_SERIE.DELETED "
                    strsql += "FROM T_WC_T2S_SERIE "
                    strsql += "LEFT JOIN T_WC_TMDB_SERIE_LANG ON T_WC_T2S_SERIE.ID_SERIE = T_WC_TMDB_SERIE_LANG.ID_SERIE "
                    strsql += "WHERE T_WC_TMDB_SERIE_LANG.LANG = 'fr' "
                    if strserieidold != "":
                        strsql += "AND T_WC_T2S_SERIE.ID_SERIE >= " + strserieidold + " "
                    strsql += "ORDER BY T_WC_T2S_SERIE.ID_SERIE ASC "
                    cursor.execute(strsql)
                    lngrowcount = cursor.rowcount
                    print(f"{lngrowcount} lines")
                    results = cursor.fetchall()
                    for row in results:
                        lngserieid = row['ID_SERIE']
                        cp.f_setservervariable("strembeddingupdateserieid",str(lngserieid),"Current serie ID in the embedding update process",0)
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
                                        print(f"ID_SERIE: {lngserieid}, {strseriefulldesc} ({strserielang}) -> DELETED")
                                    continue
                                
                                if existing_doc and len(existing_doc['ids']) > 0:
                                    strdoctext = existing_doc['documents'][0]
                                    if strdoctext == strseriefulldesc:
                                        # This document was already processed to an embedding
                                        # Nothing to do 
                                        #print(f"ID_SERIE: {lngmovieid}, {strmoviefulldesc} ({strmovielang}) -> ALREADY PROCESSED")
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
                                        #print(f"ID_SERIE: {lngserieid}, {strseriefulldesc} ({strserielang}) -> CONTENT ALREADY EXISTS")
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
                                    print(f"ID_SERIE: {lngserieid}, {strseriefulldesc} ({strserielang}) -> UPDATED")
                                else:
                                    # If the document does not exist, add it
                                    series.add(
                                        ids=[strdocid],
                                        documents=[strseriefulldesc]
                                    )
                                    print(f"ID_SERIE: {lngserieid}, {strseriefulldesc} ({strserielang}) -> ADDED")
                    # Now delete all serie embeddings that do not exist anymore in the T2S_SERIE table
                    print("Delete all serie embeddings that do not exist anymore in the T2S_SERIE table")
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
                            strsql = "SELECT ID_SERIE FROM T_WC_T2S_SERIE WHERE ID_SERIE = " + docid + " "
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
                    print(f"Deleted {lngdeletedcount} serie docs")
                    print(f"Not deleted {lngnondeletedcount} serie docs")
                    cp.f_setservervariable("strembeddingupdateseriedeletereport",f"Deleted {lngdeletedcount} serie docs (enabled)","",0)
                    cp.f_setservervariable("strembeddingupdateserienotdeletereport",f"Not deleted {lngnondeletedcount} serie docs","",0)
                    cp.f_setservervariable("strembeddingupdateserieid","","Current serie ID in the embedding update process",0)
                elif intindex == 204:
                    # Create embeddings for the persons
                    strentityname = "person"
                    strentitycollection = "persons"
                    print("Create embeddings for the " + strentitycollection)
                    strsql = ""
                    strsql += "SELECT ID_PERSON, PERSON_NAME, DELETED "
                    strsql += "FROM T_WC_T2S_PERSON "
                    if strpersonidold != "":
                        strsql += "WHERE ID_PERSON >= " + strpersonidold + " "
                    strsql += "ORDER BY ID_PERSON ASC "
                    cursor.execute(strsql)
                    lngrowcount = cursor.rowcount
                    print(f"{lngrowcount} lines")
                    results = cursor.fetchall()
                    for row in results:
                        lngpersonid = row['ID_PERSON']
                        cp.f_setservervariable("strembeddingupdatepersonid",str(lngpersonid),"Current person ID in the embedding update process",0)
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
                                #print(f"ID_PERSON: {lngpersonid}, {strpersonfulldesc} -> ALREADY PROCESSED")
                                continue
                        if intdeleted == 1:
                            # This document was deleted in the source database
                            # So we must delete it in ChromaDB
                            if existing_doc and len(existing_doc['ids']) > 0:
                                persons.delete(ids=[strdocid])
                                print(f"ID_PERSON: {lngpersonid}, {strpersonfulldesc} -> DELETED")
                                continue
                        # Check if the document exists in ChromaDB
                        if existing_doc and len(existing_doc['ids']) > 0:
                            # If the document exists, update it
                            persons.update(
                                ids=[strdocid],
                                documents=[strpersonfulldesc]  # New updated text
                            )
                            print(f"ID_PERSON: {lngpersonid}, {strpersonfulldesc} -> UPDATED")
                        else:
                            # If the document does not exist, add it
                            persons.add(
                                ids=[strdocid],
                                documents=[strpersonfulldesc]
                            )
                            print(f"ID_PERSON: {lngpersonid}, {strpersonfulldesc} -> ADDED")
                    # Now delete all person embeddings that do not exist anymore in the T2S_PERSON table
                    print("Delete all person embeddings that do not exist anymore in the T2S_PERSON table")
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
                            strsql = "SELECT ID_PERSON FROM T_WC_T2S_PERSON WHERE ID_PERSON = " + docid + " "
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
                    print(f"Deleted {lngdeletedcount} person docs")
                    print(f"Not deleted {lngnondeletedcount} person docs")
                    cp.f_setservervariable("strembeddingupdatepersondeletereport",f"Deleted {lngdeletedcount} person docs (enabled)","",0)
                    cp.f_setservervariable("strembeddingupdatepersonnotdeletereport",f"Not deleted {lngnondeletedcount} person docs","",0)
                    cp.f_setservervariable("strembeddingupdatepersonid","","Current person ID in the embedding update process",0)
                elif intindex == 205:
                    # Create embeddings for the companies
                    strentityname = "company"
                    strentitycollection = "companies"
                    print("Create embeddings for the " + strentitycollection)
                    strsql = ""
                    strsql += "SELECT ID_COMPANY, COMPANY_NAME, DELETED "
                    strsql += "FROM T_WC_T2S_COMPANY "
                    if strcompanyidold != "":
                        strsql += "WHERE ID_COMPANY >= " + strcompanyidold + " "
                    strsql += "ORDER BY ID_COMPANY ASC "
                    print(strsql)
                    cursor.execute(strsql)
                    lngrowcount = cursor.rowcount
                    print(f"{lngrowcount} lines")
                    results = cursor.fetchall()
                    for row in results:
                        lngcompanyid = row['ID_COMPANY']
                        cp.f_setservervariable("strembeddingupdatecompanyid",str(lngcompanyid),"Current company ID in the embedding update process",0)
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
                            print(f"ID_COMPANY: {lngcompanyid}, {strcompanyfulldesc} -> ADDED FORCED")
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
                                #print(f"ID_COMPANY: {lngcompanyid}, {strcompanyfulldesc} -> ALREADY PROCESSED")
                                continue
                        if intdeleted == 1:
                            # This document was deleted in the source database
                            # So we must delete it in ChromaDB
                            if existing_doc and len(existing_doc['ids']) > 0:
                                companies.delete(ids=[strdocid])
                                print(f"ID_COMPANY: {lngcompanyid}, {strcompanyfulldesc} -> DELETED")
                                continue
                        # Check if the document exists in ChromaDB
                        if existing_doc and len(existing_doc['ids']) > 0:
                            # If the document exists, update it
                            companies.update(
                                ids=[strdocid],
                                documents=[strcompanyfulldesc]  # New updated text
                            )
                            print(f"ID_COMPANY: {lngcompanyid}, {strcompanyfulldesc} -> UPDATED")
                        else:
                            # If the document does not exist, add it
                            companies.add(
                                ids=[strdocid],
                                documents=[strcompanyfulldesc]
                            )
                            print(f"ID_COMPANY: {lngcompanyid}, {strcompanyfulldesc} -> ADDED")
                    # Now delete all company embeddings that do not exist anymore in the T2S_COMPANY table
                    print("Delete all company embeddings that do not exist anymore in the T2S_COMPANY table")
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
                            strsql = "SELECT ID_COMPANY FROM T_WC_T2S_COMPANY WHERE ID_COMPANY = " + docid + " "
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
                    print(f"Deleted {lngdeletedcount} company docs")
                    print(f"Not deleted {lngnondeletedcount} company docs")
                    cp.f_setservervariable("strembeddingupdatecompanydeletereport",f"Deleted {lngdeletedcount} company docs (enabled)","",0)
                    cp.f_setservervariable("strembeddingupdatecompanynotdeletereport",f"Not deleted {lngnondeletedcount} company docs","",0)
                    cp.f_setservervariable("strembeddingupdatecompanyid","","Current company ID in the embedding update process",0)
                elif intindex == 206:
                    # Create embeddings for the networks
                    # But define some stuff first:
                    # Populate the T2S_NETWORK table
                    strentityname = "network"
                    strentitycollection = "networks"
                    print("Create embeddings for the " + strentitycollection)
                    strsql = ""
                    strsql += "SELECT ID_NETWORK, NETWORK_NAME, DELETED "
                    strsql += "FROM T_WC_T2S_NETWORK "
                    if strnetworkidold != "":
                        strsql += "WHERE ID_NETWORK >= " + strnetworkidold + " "
                    strsql += "ORDER BY ID_NETWORK ASC "
                    cursor.execute(strsql)
                    lngrowcount = cursor.rowcount
                    print(f"{lngrowcount} lines")
                    results = cursor.fetchall()
                    for row in results:
                        lngnetworkid = row['ID_NETWORK']
                        cp.f_setservervariable("strembeddingupdatenetworkid",str(lngnetworkid),"Current network ID in the embedding update process",0)
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
                                #print(f"ID_NETWORK: {lngnetworkid}, {strnetworkfulldesc} -> ALREADY PROCESSED")
                                continue
                        if intdeleted == 1:
                            # This document was deleted in the source database
                            # So we must delete it in ChromaDB
                            if existing_doc and len(existing_doc['ids']) > 0:
                                networks.delete(ids=[strdocid])
                                print(f"ID_NETWORK: {lngnetworkid}, {strnetworkfulldesc} -> DELETED")
                                continue
                        # Check if the document exists in ChromaDB
                        if existing_doc and len(existing_doc['ids']) > 0:
                            # If the document exists, update it
                            networks.update(
                                ids=[strdocid],
                                documents=[strnetworkfulldesc]  # New updated text
                            )
                            print(f"ID_NETWORK: {lngnetworkid}, {strnetworkfulldesc} -> UPDATED")
                        else:
                            # If the document does not exist, add it
                            networks.add(
                                ids=[strdocid],
                                documents=[strnetworkfulldesc]
                            )
                            print(f"ID_NETWORK: {lngnetworkid}, {strnetworkfulldesc} -> ADDED")
                    # Now delete all network embeddings that do not exist anymore in the T2S_NETWORK table
                    print("Delete all network embeddings that do not exist anymore in the T2S_NETWORK table")
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
                            strsql = "SELECT ID_NETWORK FROM T_WC_T2S_NETWORK WHERE ID_NETWORK = " + docid + " "
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
                    print(f"Deleted {lngdeletedcount} network docs")
                    print(f"Not deleted {lngnondeletedcount} network docs")
                    cp.f_setservervariable("strembeddingupdatenetworkdeletereport",f"Deleted {lngdeletedcount} network docs (enabled)","",0)
                    cp.f_setservervariable("strembeddingupdatenetworknotdeletereport",f"Not deleted {lngnondeletedcount} network docs","",0)
                    cp.f_setservervariable("strembeddingupdatenetworkid","","Current network ID in the embedding update process",0)
                elif intindex == 1207:
                    # Create embeddings for the characters
                    # But define some stuff first:
                    # What is the ID for a character?
                    # Write the SQL query to get the characters
                    strentityname = "character"
                    strentitycollection = "characters"
                    print("Create embeddings for the " + strentitycollection)
                    strsql = ""
                    strsql += "SELECT ID_CHARACTER, CHARACTER_NAME, DELETED "
                    strsql += "FROM T_WC_T2S_CHARACTER "
                    if strcharacteridold != "":
                        strsql += "WHERE ID_CHARACTER >= " + strcharacteridold + " "
                    strsql += "ORDER BY ID_CHARACTER ASC "
                    cursor.execute(strsql)
                    lngrowcount = cursor.rowcount
                    print(f"{lngrowcount} lines")
                    results = cursor.fetchall()
                    for row in results:
                        lngcharacterid = row['ID_CHARACTER']
                        cp.f_setservervariable("strembeddingupdatecharacterid",str(lngcharacterid),"Current character ID in the embedding update process",0)
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
                                #print(f"ID_CHARACTER: {lngcharacterid}, {strcharacterfulldesc} -> ALREADY PROCESSED")
                                continue
                        if intdeleted == 1:
                            # This document was deleted in the source database
                            # So we must delete it in ChromaDB
                            if existing_doc and len(existing_doc['ids']) > 0:
                                characters.delete(ids=[strdocid])
                                print(f"ID_CHARACTER: {lngcharacterid}, {strcharacterfulldesc} -> DELETED")
                                continue
                        # Check if the document exists in ChromaDB
                        if existing_doc and len(existing_doc['ids']) > 0:
                            # If the document exists, update it
                            characters.update(
                                ids=[strdocid],
                                documents=[strcharacterfulldesc]  # New updated text
                            )
                            print(f"ID_CHARACTER: {lngcharacterid}, {strcharacterfulldesc} -> UPDATED")
                        else:
                            # If the document does not exist, add it
                            characters.add(
                                ids=[strdocid],
                                documents=[strcharacterfulldesc]
                            )
                            print(f"ID_CHARACTER: {lngcharacterid}, {strcharacterfulldesc} -> ADDED")
                    # Now delete all character embeddings that do not exist anymore in the T2S_CHARACTER table
                    print("Delete all character embeddings that do not exist anymore in the T2S_CHARACTER table")
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
                            strsql = "SELECT ID_CHARACTER FROM T_WC_T2S_CHARACTER WHERE ID_CHARACTER = " + docid + " "
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
                    print(f"Deleted {lngdeletedcount} character docs")
                    print(f"Not deleted {lngnondeletedcount} character docs")
                    cp.f_setservervariable("strembeddingupdatecharacterdeletereport",f"Deleted {lngdeletedcount} character docs (enabled)","",0)
                    cp.f_setservervariable("strembeddingupdatecharacternotdeletereport",f"Not deleted {lngnondeletedcount} character docs","",0)
                    cp.f_setservervariable("strembeddingupdatecharacterid","","Current character ID in the embedding update process",0)
                elif intindex == 1208:
                    # Create embeddings for the groups
                    # But define some stuff first:
                    # Create the T2S_GROUP table
                    # Populate the T2S_GROUP table
                    # Write the SQL query to get the groups
                    strentityname = "group"
                    strentitycollection = "groups"
                    print("Create embeddings for the " + strentitycollection)
                    strsql = ""
                    strsql += "SELECT ID_GROUP, GROUP_NAME, DELETED "
                    strsql += "FROM T_WC_T2S_GROUP "
                    if strgroupidold != "":
                        strsql += "WHERE ID_GROUP >= " + strgroupidold + " "
                    strsql += "ORDER BY ID_GROUP ASC "
                    cursor.execute(strsql)
                    lngrowcount = cursor.rowcount
                    print(f"{lngrowcount} lines")
                    results = cursor.fetchall()
                    for row in results:
                        lnggroupid = row['ID_GROUP']
                        cp.f_setservervariable("strembeddingupdategroupid",str(lnggroupid),"Current group ID in the embedding update process",0)
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
                                #print(f"ID_GROUP: {lnggroupid}, {strgroupfulldesc} -> ALREADY PROCESSED")
                                continue
                        if intdeleted == 1:
                            # This document was deleted in the source database
                            # So we must delete it in ChromaDB
                            if existing_doc and len(existing_doc['ids']) > 0:
                                groups.delete(ids=[strdocid])
                                print(f"ID_GROUP: {lnggroupid}, {strgroupfulldesc} -> DELETED")
                                continue
                        # Check if the document exists in ChromaDB
                        if existing_doc and len(existing_doc['ids']) > 0:
                            # If the document exists, update it
                            groups.update(
                                ids=[strdocid],
                                documents=[strgroupfulldesc]  # New updated text
                            )
                            print(f"ID_GROUP: {lnggroupid}, {strgroupfulldesc} -> UPDATED")
                        else:
                            # If the document does not exist, add it
                            groups.add(
                                ids=[strdocid],
                                documents=[strgroupfulldesc]
                            )
                            print(f"ID_GROUP: {lnggroupid}, {strgroupfulldesc} -> ADDED")
                    # Now delete all group embeddings that do not exist anymore in the T2S_GROUP table
                    print("Delete all group embeddings that do not exist anymore in the T2S_GROUP table")
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
                            strsql = "SELECT ID_GROUP FROM T_WC_T2S_GROUP WHERE ID_GROUP = " + docid + " "
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
                    print(f"Deleted {lngdeletedcount} group docs")
                    print(f"Not deleted {lngnondeletedcount} group docs")
                    cp.f_setservervariable("strembeddingupdategroupdeletereport",f"Deleted {lngdeletedcount} group docs (enabled)","",0)
                    cp.f_setservervariable("strembeddingupdategroupnotdeletereport",f"Not deleted {lngnondeletedcount} group docs","",0)
                    cp.f_setservervariable("strembeddingupdategroupid","","Current group ID in the embedding update process",0)
                elif intindex == 209:
                    # Create embeddings for the locations (narrative location, filming location)
                    strentityname = "location"
                    strentitycollection = "locations"
                    print("Create embeddings for the " + strentitycollection)
                    strsql = ""
                    strsql += "SELECT DISTINCT T_WC_WIKIDATA_ITEM_PROPERTY.ID_ITEM, 'en' AS ENGLISH_LANGUAGE, t2s.ITEM_LABEL, 'fr' AS FRENCH_LANGUAGE, t2s.ITEM_LABEL_FR, t2s.DELETED "
                    strsql += "FROM T_WC_WIKIDATA_ITEM_PROPERTY "
                    strsql += "INNER JOIN T_WC_T2S_ITEM t2s ON T_WC_WIKIDATA_ITEM_PROPERTY.ID_ITEM = t2s.ID_WIKIDATA "
                    strsql += "WHERE T_WC_WIKIDATA_ITEM_PROPERTY.ID_PROPERTY IN ('P840', 'P915') "
                    if strlocationidold != "":
                        strsql += "AND T_WC_WIKIDATA_ITEM_PROPERTY.ID_ITEM >= '" + strlocationidold + "' "
                    strsql += "ORDER BY T_WC_WIKIDATA_ITEM_PROPERTY.ID_ITEM ASC "
                    cursor.execute(strsql)
                    lngrowcount = cursor.rowcount
                    print(f"{lngrowcount} lines")
                    results = cursor.fetchall()
                    for row in results:
                        strlocationid = row['ID_ITEM']
                        cp.f_setservervariable("strembeddingupdatelocationid",strlocationid,"Current location ID in the embedding update process",0)
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
                                    print(f"ID_ITEM: {strlocationid}, {strlocationfulldesc} -> DELETED")
                                    continue
                                
                                if existing_doc and len(existing_doc['ids']) > 0:
                                    strdoctext = existing_doc['documents'][0]
                                    if strdoctext == strlocationfulldesc:
                                        # This document was already processed to an embedding
                                        # Nothing to do 
                                        #print(f"ID_ITEM: {strlocationid}, {strlocationfulldesc} -> ALREADY PROCESSED")
                                        continue
                                
                                # Check if the document exists in ChromaDB
                                if existing_doc and len(existing_doc['ids']) > 0:
                                    locations.update(
                                        ids=[strdocid],
                                        documents=[strlocationfulldesc],
                                        metadatas=[{"id": strlocationid, "language": lang_code}]                                        
                                    )
                                    print(f"ID_ITEM: {strlocationid}, {strlocationfulldesc} -> UPDATED")
                                else:
                                    # Add it to the collection
                                    locations.add(
                                        ids=[strdocid],
                                        documents=[strlocationfulldesc],
                                        metadatas=[{"id": strlocationid, "language": lang_code}]                                        
                                )
                                print(f"ID_ITEM: {strlocationid}, {strlocationfulldesc} -> ADDED")

                    # Now delete all location embeddings that do not exist anymore in the T2S_ITEM table
                    print("Delete all location embeddings that do not exist anymore in the T2S_ITEM table")
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
                            strsql = "SELECT ID_WIKIDATA FROM T_WC_T2S_ITEM WHERE ID_WIKIDATA = '" + docid + "' "
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
                    print(f"Deleted {lngdeletedcount} location docs")
                    print(f"Not deleted {lngnondeletedcount} location docs")
                    cp.f_setservervariable("strembeddingupdatelocationdeletereport",f"Deleted {lngdeletedcount} location docs (enabled)","",0)
                    cp.f_setservervariable("strembeddingupdatelocationnotdeletereport",f"Not deleted {lngnondeletedcount} location docs","",0)
                    cp.f_setservervariable("strembeddingupdatelocationid","","Current location ID in the embedding update process",0)

                if intindex == 209:
                    # Last process is finished
                    cp.f_setservervariable("strembeddingupdatecurrentcontent","","Current content processed in the embedding update process",0)
            # Calculate total runtime and convert to readable format
            end_time = time.time()
            strtotalruntime = int(end_time - start_time)  # Total runtime in seconds
            readable_duration = cp.convert_seconds_to_duration(strtotalruntime)
            cp.f_setservervariable("strembeddingupdatetotalruntime",readable_duration,strtotalruntimedesc,0)
            print(f"Total runtime: {strtotalruntime} seconds ({readable_duration})")
except pymysql.MySQLError as e:
    print(f"? MySQL Error: {e}")
    cp.connectioncp.rollback()
