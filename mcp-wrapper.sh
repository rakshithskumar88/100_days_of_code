#!/usr/bin/env bash

PROJECT_DIR="/home/rakshithskumar/100_days_of_code"

# 1. Silence direnv to prevent JSON-RPC corruption
export DIRENV_LOG_FORMAT=""

# 2. WIRETAP: Redirect all crash logs to a text file we can actually read
exec 2> "$PROJECT_DIR/mcp-error.log"

# 3. DIRECT EXECUTION: Bypass symlinks and force Node to run the raw JS file
exec /etc/profiles/per-user/rakshithskumar/bin/direnv exec "$PROJECT_DIR" node "$PROJECT_DIR/node_modules/@modelcontextprotocol/server-filesystem/dist/index.js" "$PROJECT_DIR"