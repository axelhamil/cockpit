#!/bin/sh
set -u

state_home=${COCKPIT_HOME:-${HOME:-}/.cockpit}

if [ ! -d "$state_home" ]; then
  exit 0
fi

if [ "$(uname -s)" = Darwin ] && ! xcode-select -p >/dev/null 2>&1; then
  exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
  exit 0
fi

script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd) || exit 0

python3 "$script_dir/prompt_check.py" </dev/null 2>/dev/null || true

exit 0
