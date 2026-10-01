#!/usr/bin/env bash
# ==============================================================================
# LELE QUIZ — HERMES AGENT LAUNCHER
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# Nạp môi trường cục bộ nếu có
[ -f "${SCRIPT_DIR}/env.sh" ] && source "${SCRIPT_DIR}/env.sh"

# Đảm bảo PATH nhận diện hermes
export PATH="/home/vpsg16gb/.local/bin:${PATH}"

# Định vị file thực thi hermes
HERMES_BIN="$(which hermes 2>/dev/null || echo "/home/vpsg16gb/.local/bin/hermes")"

if [ ! -x "${HERMES_BIN}" ]; then
    echo "❌ Không tìm thấy Hermes executable tại: ${HERMES_BIN}"
    exit 1
fi

echo "🚀 [Hermes Agent] Khởi chạy Hermes trong thư mục: ${SCRIPT_DIR}"
exec "${HERMES_BIN}" "$@"
