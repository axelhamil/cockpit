#!/bin/sh
set -eu

if [ "${COCKPIT_TEST:-}" != 1 ]; then
  unset RAILWAY_BIN COCKPIT_CLIPBOARD COCKPIT_OPEN COCKPIT_OPEN_DELAY GH_BIN COCKPIT_BIN_DIR COCKPIT_SHELL_PROFILE CLAUDE_SETTINGS
fi

gh_bin=${GH_BIN:-gh}
open_command=${COCKPIT_OPEN:-open}
open_delay=${COCKPIT_OPEN_DELAY:-3}

fail() {
  printf '%s\n' "$1" >&2
  exit 1
}

printf '%s\n' "GitHub sign-in: a one-time code is copied to the clipboard and the GitHub page opens. Paste the code there and approve."

(sleep "$open_delay" && sh -c "$open_command https://github.com/login/device") >/dev/null 2>&1 &
opener=$!
trap 'kill "$opener" 2>/dev/null || :' EXIT

if ! "$gh_bin" auth login --hostname github.com --git-protocol https --web --clipboard; then
  fail "The GitHub sign-in did not finish. Retry, and approve in the browser before the code expires."
fi

if ! "$gh_bin" auth setup-git --hostname github.com; then
  fail "The sign-in worked but git could not be set up to use it. Retry this step."
fi

"$gh_bin" auth status --hostname github.com
