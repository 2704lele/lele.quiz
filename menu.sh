#!/usr/bin/env bash
cd "$(dirname "$0")"
[ -f ./env.sh ] && source ./env.sh
exec python3 menu.py "$@"
