#!/usr/bin/env bash
cd "$(dirname "$0")"
[ -f ./env.sh ] && source ./env.sh
PIPELINE="${1:-all}"
COUNT="${2:-1}"
echo "🚀 [Quick Idea] Sinh ${COUNT} batch cho pipeline: ${PIPELINE}..."
exec python3 scripts/generate_daily_batches.py --pipeline "${PIPELINE}" --count "${COUNT}"
