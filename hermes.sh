#!/usr/bin/env bash
# ==============================================================================
# LELE QUIZ — HERMES AGENT SHORTCUT
# ==============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/run_hermes.sh" "$@"
