#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
[ -f ./env.sh ] && source ./env.sh

if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    exec python3 scripts/run_ideation_dispatcher.py --help
fi

PIPELINE="${1:-all}"
COUNT="${2:-1}"
echo "🚀 [Quick Idea] Sinh ${COUNT} batch cho pipeline/tab: ${PIPELINE}..."
exec python3 scripts/run_ideation_dispatcher.py --tab "${PIPELINE}" --count "${COUNT}"
