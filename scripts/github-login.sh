#!/bin/sh
set -eu

if [ "${RP_TEST:-}" != 1 ]; then
  unset RAILWAY_BIN RP_PSQL RP_CLIPBOARD RP_PUBLIC_HOST RP_PUBLIC_PORT RP_PASTE RP_CLEAR_CLIPBOARD GH_BIN RP_BIN_DIR RP_SHELL_PROFILE CLAUDE_SETTINGS
fi

paste_command=${RP_PASTE:-pbpaste}
clear_command=${RP_CLEAR_CLIPBOARD:-pbcopy}
gh_bin=${GH_BIN:-gh}

fail() {
  printf '%s\n' "$1" >&2
  exit 1
}

empty_clipboard() {
  printf '' | sh -c "$clear_command" >/dev/null 2>&1 || true
}

without_token() {
  while IFS= read -r line || [ -n "$line" ]; do
    case $line in
      *"$token"*) ;;
      *) printf '%s\n' "$line" ;;
    esac
  done
}

token=$(sh -c "$paste_command" 2>/dev/null | tr -d '[:space:]') || token=

case $token in
  github_pat_?*) ;;
  *)
    fail "The clipboard does not hold a GitHub fine-grained token. Copy the token from the GitHub page again, then retry."
    ;;
esac

trap empty_clipboard EXIT

login_status=0
login_output=$(printf '%s' "$token" | "$gh_bin" auth login --with-token --hostname github.com --git-protocol https 2>&1) || login_status=$?

if [ "$login_status" -ne 0 ]; then
  printf '%s\n' "GitHub did not accept the token, so nothing was saved and the clipboard was emptied. Create a new fine-grained token for the repository, copy it, then retry. Answer from GitHub:" >&2
  printf '%s\n' "$login_output" | without_token >&2
  exit 1
fi

if ! "$gh_bin" auth setup-git --hostname github.com; then
  fail "The token was accepted but git could not be set up to use it. Retry this step, and ask a developer if it fails again."
fi

if ! status_output=$("$gh_bin" auth status --hostname github.com 2>&1); then
  fail "The token was saved but GitHub does not confirm the login. Retry this step, and ask a developer if it fails again."
fi

printf '%s\n' "$status_output" | without_token
