#!/bin/bash
set -e

# ToonForge dev server launcher (macOS/Linux)
# Builds frontend if needed, starts backend API, and opens the browser.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$REPO_ROOT/frontend"
BACKEND_DIR="$REPO_ROOT/backend"
FRONTEND_DIST="$FRONTEND_DIR/dist"

echo "Starting ToonForge dev servers..."

# Build frontend if dist doesn't exist
if [ ! -d "$FRONTEND_DIST" ]; then
    echo "Building frontend..."
    cd "$FRONTEND_DIR"
    npm run build
    cd "$REPO_ROOT"
fi

# Start backend API
echo "Starting API server on http://127.0.0.1:8000"
cd "$BACKEND_DIR"
.venv/bin/uvicorn app.main:app --port 8000 &
BACKEND_PID=$!

# Wait for API to start
sleep 2

# Open browser
if command -v open &> /dev/null; then
    open http://127.0.0.1:8000
else
    echo "Open http://127.0.0.1:8000 in your browser."
fi

# Keep process running
wait $BACKEND_PID
