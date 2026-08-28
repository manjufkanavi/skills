#!/bin/bash
# browser-skill-init.sh
# Initializes the browser skill environment on first run

PROFILE_DIR="/Users/manjunath/.nanobot/browser-profile"
STORAGE_STATE="$PROFILE_DIR/storage-state.json"

# Create profile directory if it doesn't exist
mkdir -p "$PROFILE_DIR"

# Create a default empty storage state if it doesn't exist
if [ ! -f "$STORAGE_STATE" ]; then
    echo '{"cookies":[],"origins":[]}' > "$STORAGE_STATE"
fi

echo "Browser skill initialized."
echo "Profile directory: $PROFILE_DIR"
echo "Storage state: $STORAGE_STATE"
echo "Browser will run in headed (non-headless) mode with persistent sessions."
