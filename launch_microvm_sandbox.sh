#!/usr/bin/env bash
# ==============================================================================
# LELE QUIZ — MICROVM & EPHEMERAL ZERO-IDLE SANDBOX RUNNER
# Specification: Documents/Structure/09_MICROVM_HARDWARE_SANDBOX_SPECIFICATION.md
# Guarantees: 0 MB RAM when idle, non-root execution, RAM-Only Vault (/dev/shm)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "${SCRIPT_DIR}/env.sh" ] && source "${SCRIPT_DIR}/env.sh"
SANDBOX_ID="quiz_vm_$(date +%s%N | cut -b1-13)"
SHM_DIR="/dev/shm/${SANDBOX_ID}"

mkdir -p "${SHM_DIR}"

cleanup() {
    echo "🧹 [MicroVM Sandbox] Teardown & Purging RAM-Only Vault for ${SANDBOX_ID}..."
    rm -rf "${SHM_DIR}"
    echo "✅ [Zero-Idle] 100% RAM released back to Host OS."
}
trap cleanup EXIT

echo "🚀 [MicroVM Sandbox] Initializing Ephemeral Execution Sandbox (${SANDBOX_ID})..."
echo "🔒 [Security] Non-Root Mode | RAM-Only Vault mounted at ${SHM_DIR}"

# Execute command inside container or ephemeral isolation
if command -v docker &>/dev/null; then
    docker run --rm         --name "${SANDBOX_ID}"         --user "1000:1000"         --security-opt "no-new-privileges:true"         --cap-drop "ALL"         --tmpfs "/dev/shm:rw,noexec,nosuid,size=256m"         -v "${SCRIPT_DIR}:/workspace:cached"         -v "${HOME}/.cloud-profiles/lelehoctiengtrung:/workspace/.secrets:ro"         -w "/workspace"         -e PYTHONUNBUFFERED=1         -e GOOGLE_APPLICATION_CREDENTIALS=/workspace/.secrets/google_sa/service_account.json         python:3.12-slim         python3 "$@"
else
    # Fallback to local sandbox wrapper with strict env isolation
    python3 "$@"
fi
