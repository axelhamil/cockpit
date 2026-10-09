#!/bin/sh
set -eu

LC_ALL=C
export LC_ALL

if [ "${COCKPIT_TEST:-}" != 1 ]; then
  unset RAILWAY_BIN COCKPIT_CLIPBOARD COCKPIT_OPEN COCKPIT_OPEN_DELAY GH_BIN COCKPIT_BIN_DIR COCKPIT_SHELL_PROFILE CLAUDE_SETTINGS
fi

settings_file=${CLAUDE_SETTINGS:-$HOME/.claude/settings.json}
script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
usage='Usage: apply-settings.sh --marketplace <name> --repo <owner/repo> | apply-settings.sh --remove --marketplace <name>'

marketplace=
repo=
mode=apply

fail_usage() {
  printf '%s\n' "$1" >&2
  exit 2
}

valid_marketplace() {
  case $1 in
    '' | [!A-Za-z0-9]* | *[!A-Za-z0-9._-]*) return 1 ;;
  esac
}

valid_repo() {
  case $1 in
    */*/* | *[!A-Za-z0-9._/-]*) return 1 ;;
    ?*/?*) return 0 ;;
  esac
  return 1
}

while [ $# -gt 0 ]; do
  if [ "$1" = --remove ]; then
    mode=remove
    shift
    continue
  fi

  case $1 in
    --marketplace | --repo)
      if [ $# -lt 2 ]; then
        fail_usage "The option $1 needs a value."
      fi
      ;;
    *)
      fail_usage "Unknown option '$1'. $usage"
      ;;
  esac

  case $1 in
    --marketplace) marketplace=$2 ;;
    --repo) repo=$2 ;;
  esac
  shift 2
done

if ! valid_marketplace "$marketplace"; then
  fail_usage "The marketplace name is missing or holds unexpected characters. Use the name written in the plugin marketplace file. $usage"
fi

if [ "$mode" = remove ] && [ -n "$repo" ]; then
  fail_usage "The option --repo is not used with --remove. $usage"
fi

if [ "$mode" = apply ] && ! valid_repo "$repo"; then
  fail_usage "The plugin repository is missing or is not written as owner/repo. $usage"
fi

if ! command -v python3 >/dev/null 2>&1; then
  printf '%s\n' "python3 is missing, so the settings cannot be written. Install the Apple Command Line Tools first, then run this step again." >&2
  exit 1
fi

exec python3 "$script_dir/apply_settings.py" "$mode" "$settings_file" "$script_dir/permissions.json" "$marketplace" "$repo"
