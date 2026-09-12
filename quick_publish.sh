#!/usr/bin/env bash
# ==============================================================================
# LELE QUIZ — QUICK SOCIAL MEDIA PUBLISHING SHORTCUT
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "${SCRIPT_DIR}/env.sh" ] && source "${SCRIPT_DIR}/env.sh"

TAB="${1:-pinyin}"
ROW_ID="${2:-2}"
CHANNELS="${3:-buffer1}"
shift 3 2>/dev/null || shift $# 2>/dev/null || true

echo "🚀 [Quick Publish] Tab: $TAB | Row: #$ROW_ID | Channels: $CHANNELS"
python3 "${SCRIPT_DIR}/scripts/publish_social_batch.py" --tab "$TAB" --id "$ROW_ID" --channels "$CHANNELS" "$@"
