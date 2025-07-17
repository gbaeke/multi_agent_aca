#!/bin/bash

# Build the Docker image for x64 platform
docker build --platform linux/amd64 -t multi-agent-conversation .

# Check if --run parameter is provided
if [[ "$1" == "--run" ]]; then
    echo "Running the container..."
    # Run the container with environment variables from .env
    docker run -it --env-file .env -p 8000:8000 multi-agent-conversation
else
    echo "Docker image built successfully for x64 platform. Use '--run' parameter to also run the container."
fi 