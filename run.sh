#!/bin/bash
# morning-edition runner — called by cron at 7am
# Usage: ./run.sh [optional: path to python3]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${1:-python3}"
LOG="$SCRIPT_DIR/magazines/run.log"

mkdir -p "$SCRIPT_DIR/magazines"

echo "" >> "$LOG"
echo "=== $(date '+%Y-%m-%d %H:%M:%S') ===" >> "$LOG"

# Requires ANTHROPIC_API_KEY in environment. If using cron, add it to crontab
# or source it from a dotfile:
# source "$HOME/.env" && python generate.py
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    # Try sourcing common dotfiles
    for f in "$HOME/.env" "$HOME/.envrc" "$HOME/.profile" "$HOME/.bash_profile"; do
        [ -f "$f" ] && source "$f" 2>/dev/null && break
    done
fi

cd "$SCRIPT_DIR"
"$PYTHON" generate.py >> "$LOG" 2>&1

echo "Done." >> "$LOG"
