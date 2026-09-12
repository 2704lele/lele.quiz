#!/bin/bash
# ==============================================================================
# Script: run_ideation.sh
# Purpose: Trigger Zero-Secret Serverless Ideation Pipeline on Cloudflare & GitHub Actions
# ==============================================================================

set -e

COUNT=${1:-5}
MODULE=${2:-"pinyin"}

case "$MODULE" in
  pinyin|pinyinquiz)
    WORKER_URL="https://lele-pinyinquiz.hothihuong113.workers.dev/api/trigger-ideation"
    ;;
  vocabcn|vocabCNquiz)
    WORKER_URL="https://lele-vocabcnquiz.hothihuong113.workers.dev/api/trigger-ideation"
    ;;
  vocabvn|vocabVNquiz)
    WORKER_URL="https://lele-vocabvnquiz.hothihuong113.workers.dev/api/trigger-ideation"
    ;;
  *)
    WORKER_URL="https://lele-pinyinquiz.hothihuong113.workers.dev/api/trigger-ideation"
    ;;
esac

echo "🚀 Kích hoạt Ideation Pipeline..."
echo "• Module: $MODULE"
echo "• Số lượng (count): $COUNT"
echo "• Endpoint: $WORKER_URL"
echo ""

RESPONSE=$(curl -s "${WORKER_URL}?count=${COUNT}")

echo "Response từ Cloudflare Orchestrator:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""
echo "✅ Workflow đã được dispatch lên GitHub Actions Runner."
