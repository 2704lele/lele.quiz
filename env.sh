#!/usr/bin/env bash
export PYTHONDONTWRITEBYTECODE=1
VENV_PATH="/home/vpsg16gb/.venvs/lele_quiz"
if [ -d "$VENV_PATH/bin" ]; then
  export VIRTUAL_ENV="$VENV_PATH"
  export PATH="$VENV_PATH/bin:$PATH"
fi
