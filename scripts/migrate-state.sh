#!/bin/sh
set -eu

if [ "${COCKPIT_TEST:-}" != 1 ]; then
  unset COCKPIT_MIGRATION_FAIL_AT COCKPIT_MIGRATION_KILL_AT COCKPIT_MIGRATION_LOCK_WAIT
fi

state_home=${COCKPIT_HOME:-${HOME:-}/.cockpit}
script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)

if [ ! -e "$state_home/state.md" ] && [ ! -e "$state_home/cockpit.md" ]; then
  exit 0
fi

python_is_ready() {
  if [ "$(uname -s)" = Darwin ] && ! xcode-select -p >/dev/null 2>&1; then
    return 1
  fi

  command -v python3 >/dev/null 2>&1
}

if ! python_is_ready; then
  if [ ! -e "$state_home/cockpit.md" ]; then
    printf '%s\n' 'migration: failed (python3 is not available)'
  fi
  exit 0
fi

exec python3 "$script_dir/migrate_state.py" "$state_home"
