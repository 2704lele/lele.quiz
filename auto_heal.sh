#!/usr/bin/env bash
# ==============================================================================
# LELE QUIZ — UNIVERSAL AUTO-HEALING CLI WRAPPER
# Enforces PYTHONDONTWRITEBYTECODE=1 and isolated virtualenv
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "${SCRIPT_DIR}/env.sh" ] && source "${SCRIPT_DIR}/env.sh"

if [ -f "$SCRIPT_DIR/scripts/auto_heal.py" ]; then
    exec python3 "$SCRIPT_DIR/scripts/auto_heal.py" "$@"
elif [ -f "$SCRIPT_DIR/scripts/hermes_agy_repair.py" ]; then
    exec python3 "$SCRIPT_DIR/scripts/hermes_agy_repair.py" "$@"
else
    echo "Error: Neither scripts/auto_heal.py nor scripts/hermes_agy_repair.py found." >&2
    exit 1
fi
