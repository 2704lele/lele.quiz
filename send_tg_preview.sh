#!/usr/bin/env bash
# ==============================================================================
# LELE QUIZ — SEND REVIEW POST TO TELEGRAM SHORTCUT
# Usage: ./send_tg_preview.sh <tab> <row_id>
# Example: ./send_tg_preview.sh pinyin 16
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "${SCRIPT_DIR}/env.sh" ] && source "${SCRIPT_DIR}/env.sh"

TAB="${1:-pinyin}"
ROW_ID="${2:-2}"

echo "📱 [Telegram Preview] Sending review card for Tab: $TAB | Row: #$ROW_ID..."
python3 "${SCRIPT_DIR}/scripts/telegram_interactive_bot.py" preview "$TAB" "$ROW_ID"
