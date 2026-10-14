#!/bin/bash
set -e
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo 'Python 3.9 以降をインストールしてください。'
  exit 1
fi
exec python3 bootstrap.py "$@"
