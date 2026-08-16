#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "subagents-dispatch Hook launcher requires exactly one script path" >&2
  exit 64
fi

script=$1
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 && \
     "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then
    exec "$candidate" "$script"
  fi
done

echo "subagents-dispatch Hook requires Python 3.11 or newer; spawn guard unavailable" >&2
exit 78
