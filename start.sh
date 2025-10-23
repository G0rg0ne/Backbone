#!/bin/bash

# Start the document processor API
echo "Starting document processor API..."
cd document_processor
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for document processor to start
echo "Waiting for document processor to start..."
sleep 5

# Start the frontend
echo "Starting frontend..."
cd ..
reflex run --frontend-port 3000 --backend-port 8001

# Cleanup function
cleanup() {
    echo "Stopping services..."
    kill $BACKEND_PID 2>/dev/null
    exit
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Wait for background process
wait $BACKEND_PID
