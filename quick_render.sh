#!/usr/bin/env bash
# ==============================================================================
# LELE CHINESE QUIZ — QUICK RENDER DISPATCHER (100% GOOGLE COLAB CLI)
# ==============================================================================

cd "$(dirname "$0")"
[ -f ./env.sh ] && source ./env.sh

PIPELINE="${1:-all}"
ROW_ID="${2:-}"
QUALITY="${3:-qh}"

if [ "${PIPELINE}" = "all" ]; then
  echo "🎬 Kích hoạt Google Colab Batch Continuity Runner: Quét và render TOÀN BỘ dòng Pending trên cả 4 tabs..."
  exec python3 scripts/colab_render_cli.py --pipeline all --quality "${QUALITY}"
fi

if [ -z "${ROW_ID}" ]; then
  echo "Cách dùng:"
  echo "  Render toàn bộ dòng Pending cả 4 tabs: ./quick_render.sh all"
  echo "  Render dòng cụ thể:                   ./quick_render.sh [pinyin|vocabcn|vocabvn|multilevels] [ROW_ID] [QUALITY(qh/ql)]"
  echo "Ví dụ:"
  echo "  ./quick_render.sh all"
  echo "  ./quick_render.sh pinyin 24"
  echo "  ./quick_render.sh vocabcn 10 qh"
  exit 1
fi

echo "🎬 Kích hoạt Google Colab Render cho Batch #${ROW_ID} (${PIPELINE})..."
exec python3 scripts/colab_render_cli.py --pipeline "${PIPELINE}" --row "${ROW_ID}" --quality "${QUALITY}"
