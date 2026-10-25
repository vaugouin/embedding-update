#!/bin/bash

# Switched off by off.sh, back on with on.sh: the flag file CRON_OFF next to this script makes
# every cron tick exit here. The script keeps its name, so the git clone stays clean.
if [ -f "$(dirname "$(readlink -f "$0")")/CRON_OFF" ]; then
    echo "CRON_OFF present: embedding-update switched off (bash on.sh to switch it back on)."
    exit 0
fi

# Ensure ChromaDB is healthy before starting the embedding update. The job
# connects to Chroma at import time and crashes immediately if it is down, so
# recover it first (or skip cleanly rather than emit a traceback).
if ! bash "$HOME/docker/chromadb/chromadb-ensure.sh"; then
    echo "ChromaDB unavailable and could not be recovered — skipping embedding-update run."
    exit 1
fi

# Check if the embedding-update Docker container is running
if [ $(docker ps -q -f name=embedding-update) ]; then
    echo "embedding-update Docker container is already running."
else
    # Start the embedding-update container if it is not running
    # Create shared_data folder if it doesn't exist
    mkdir -p $HOME/docker/shared_data
    cd $HOME/docker/embedding-update
    docker build -t embedding-update-python-app .
    # docker run -it --rm --network="host" --env-file /home/debian/docker/embedding-update/.env --name embedding-update embedding-update-python-app
    docker run -d --rm --network="host" --env-file /home/debian/docker/embedding-update/.env --name embedding-update embedding-update-python-app
    echo "embedding-update Docker container started."
fi
