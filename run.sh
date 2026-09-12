#!/usr/bin/env bash
# ==============================================================================
# LELE QUIZ — ROOT ENTRYPOINT RUNNER
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "${SCRIPT_DIR}/env.sh" ] && source "${SCRIPT_DIR}/env.sh"

exec "${SCRIPT_DIR}/menu.sh" "$@"
