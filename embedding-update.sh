#!/bin/bash

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
