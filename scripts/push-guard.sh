#!/bin/sh
set -u

if [ "${COCKPIT_TEST:-}" != 1 ]; then
  unset COCKPIT_GIT_BUDGET
fi

input=$(cat 2>/dev/null) || exit 0

case $input in
  *push*) ;;
  *) exit 0 ;;
esac

if [ "$(uname -s)" = Darwin ] && ! xcode-select -p >/dev/null 2>&1; then
  exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
  exit 0
fi

script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd) || exit 0

printf '%s\n' "$input" | python3 "$script_dir/push_guard.py" 2>/dev/null || true

exit 0
