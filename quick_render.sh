#!/usr/bin/env bash
# ==============================================================================
# LELE CHINESE QUIZ — QUICK RENDER DISPATCHER (100% GITHUB ACTIONS ENGINE)
# ==============================================================================

cd "$(dirname "$0")"
[ -f ./env.sh ] && source ./env.sh

PIPELINE="${1:-all}"
ROW_ID="${2:-}"
QUALITY="${3:-qh}"

exec python3 scripts/run_render_dispatcher.py --tab "${PIPELINE}" --row "${ROW_ID}" --quality "${QUALITY}"
